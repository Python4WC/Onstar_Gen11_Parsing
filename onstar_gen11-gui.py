import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
from pathlib import Path
import binascii
import re
import struct
from datetime import datetime, timezone
from tkinterdnd2 import DND_FILES, TkinterDnD
from openpyxl import Workbook
import platform

if platform.system() == "Windows":
    import ctypes
    from ctypes import windll

class OnStarDecoder:
    def __init__(self):
        # GPS epoch start: January 6, 1980 00:00:00 UTC (first Sunday of 1980)
        self.gps_epoch = datetime(1980, 1, 6, 0, 0, 0, tzinfo=timezone.utc)

    def extract_gps_data(self, file_path, output_xlsx_path, progress_callback=None):
        """Extract GPS data from OnStar binary file and decode it to XLSX"""
        try:
            if progress_callback:
                progress_callback("Reading binary file...", 10)
            with open(file_path, 'rb') as f:
                data = f.read()
            if progress_callback:
                progress_callback("Finding GPS data blocks...", 30)
            gps_blocks = self.find_gps_blocks_binary(data)
            if progress_callback:
                progress_callback(f"Parsing {len(gps_blocks)} GPS blocks...", 50)
            parsed_entries = []
            for i, block in enumerate(gps_blocks):
                entry = self.parse_gps_block(block)
                if entry and self.is_valid_entry(entry):
                    parsed_entries.append(entry)
                if progress_callback and len(gps_blocks) > 0:
                    progress = 50 + (30 * (i + 1) // len(gps_blocks))
                    progress_callback(f"Parsing block {i+1}/{len(gps_blocks)}", progress)
            if progress_callback:
                progress_callback("Writing XLSX file...", 85)
            wb = Workbook()
            ws = wb.active
            ws.title = "GPS Data"
            headers = ['lat', 'long', 'utc_year', 'utc_month', 'utc_day', 'utc_hour', 'utc_min', 
                      'timestamp_time', '', '', '', '', '', '', 'lat_hex', 'lon_hex']
            ws.append(headers)
            for entry in parsed_entries:
                ws.append([
                    entry['lat'],
                    entry['long'],
                    entry['utc_year'],
                    entry['utc_month'],
                    entry['utc_day'],
                    entry['utc_hour'],
                    entry['utc_min'],
                    entry['timestamp_time'],
                    '', '', '', '', '', '',  # Six blank columns
                    entry['lat_hex'],
                    entry['lon_hex']
                ])
            wb.save(output_xlsx_path)
            if progress_callback:
                progress_callback("Complete!", 100)
            return len(parsed_entries), None
        except FileNotFoundError:
            return 0, f"File not found: {file_path}"
        except Exception as e:
            return 0, f"Error processing file: {str(e)}"

    def find_gps_blocks_binary(self, data):
        """Find GPS data blocks in binary data"""
        blocks = []
        text_data = data.decode('latin-1', errors='ignore')
        gps_patterns = [
            b'gps_tow=',
            b'gps_week=', 
            b'utc_year=',
            b'lat=',
            b'lon='
        ]
        keyword_positions = []
        for pattern in gps_patterns:
            pattern_str = pattern.decode('latin-1')
            for match in re.finditer(re.escape(pattern_str), text_data):
                keyword_positions.append(match.start())
        if not keyword_positions:
            return blocks
        keyword_positions.sort()
        i = 0
        while i < len(keyword_positions):
            block_start = keyword_positions[i]
            block_end = block_start + 200
            j = i + 1
            while j < len(keyword_positions) and keyword_positions[j] - block_start < 1000:
                block_end = max(block_end, keyword_positions[j] + 200)
                j += 1
            start_pos = max(0, block_start - 50)
            end_pos = min(len(text_data), block_end + 50)
            block_text = text_data[start_pos:end_pos]
            blocks.append(block_text)
            i = j
        return blocks

    def parse_gps_block(self, block_text):
        """Parse a GPS data block into structured data"""
        entry = {
            'lat': 'ERROR',
            'long': 'ERROR', 
            'utc_year': '',
            'utc_month': '',
            'utc_day': '',
            'utc_hour': '',
            'utc_min': '',
            'timestamp_time': 'ERROR',
            'lat_hex': '',
            'lon_hex': ''
        }
        try:
            gps_tow = self.extract_number_flexible(block_text, [r'gps_tow=(\d+)', r'tow=(\d+)'])
            gps_week = self.extract_number_flexible(block_text, [r'gps_week=(\d+)', r'week=(\d+)'])
            utc_year = self.extract_number_flexible(block_text, [r'utc_year=(\d+)', r'year=(\d{4})'])
            utc_month = self.extract_number_flexible(block_text, [r'utc_month=(\d+)', r'month=(\d+)'])
            utc_day = self.extract_number_flexible(block_text, [r'utc_day=(\d+)', r'day=(\d+)'])
            utc_hour = self.extract_number_flexible(block_text, [r'utc_hour=(\d+)', r'hour=(\d+)'])
            utc_min = self.extract_number_flexible(block_text, [r'utc_min=(\d+)', r'min=(\d+)'])
            entry['utc_year'] = utc_year if utc_year is not None else ''
            entry['utc_month'] = utc_month if utc_month is not None else ''
            entry['utc_day'] = utc_day if utc_day is not None else ''
            entry['utc_hour'] = utc_hour if utc_hour is not None else ''
            entry['utc_min'] = utc_min if utc_min is not None else ''
            lat_hex = self.extract_hex_flexible(block_text, [r'lat=([0-9A-Fa-f]{16})', r'lat=([0-9A-Fa-f\s]{16,})'])
            lon_hex = self.extract_hex_flexible(block_text, [r'lon=([0-9A-Fa-f]{16})', r'lon=([0-9A-Fa-f\s]{16,})'])
            entry['lat_hex'] = lat_hex if lat_hex else ''
            entry['lon_hex'] = lon_hex if lon_hex else ''
            if gps_tow is not None and gps_week is not None:
                try:
                    if 0 <= gps_tow <= 604800000 and 0 <= gps_week <= 4000:
                        gps_tow_sec = gps_tow / 1000.0
                        gps_week_sec = gps_week * 604800
                        total_seconds = gps_week_sec + gps_tow_sec
                        gps_timestamp = self.gps_epoch.timestamp() + total_seconds
                        dt = datetime.fromtimestamp(gps_timestamp, tz=timezone.utc)
                        entry['timestamp_time'] = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                except Exception:
                    pass
            if lat_hex:
                try:
                    clean_hex = re.sub(r'[^0-9A-Fa-f]', '', lat_hex)
                    if len(clean_hex) == 16:
                        lat_bytes = bytes.fromhex(clean_hex)
                        lat_raw = struct.unpack('<d', lat_bytes)[0]
                        lat_decimal = lat_raw / 10000000.0
                        if -90 <= lat_decimal <= 90:
                            entry['lat'] = lat_decimal
                except Exception:
                    entry['lat'] = 'ERROR'
            if lon_hex:
                try:
                    clean_hex = re.sub(r'[^0-9A-Fa-f]', '', lon_hex)
                    if len(clean_hex) == 16:
                        lon_bytes = bytes.fromhex(clean_hex)
                        lon_raw = struct.unpack('<d', lon_bytes)[0]
                        lon_decimal = lon_raw / 10000000.0
                        if -180 <= lon_decimal <= 180:
                            entry['long'] = lon_decimal
                except Exception:
                    entry['long'] = 'ERROR'
            return entry
        except Exception:
            return None

    def extract_number_flexible(self, text, patterns):
        """Extract a number using multiple regex patterns"""
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = int(match.group(1))
                    return value
                except:
                    continue
        return None

    def extract_hex_flexible(self, text, patterns):
        """Extract hex value using multiple regex patterns"""
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                hex_val = match.group(1)
                clean_hex = re.sub(r'[^0-9A-Fa-f]', '', hex_val)
                if len(clean_hex) >= 16:
                    return clean_hex[:16]
        return None

    def is_valid_entry(self, entry):
        """Check if entry has at least some valid data"""
        if not entry:
            return False
        if entry['lat'] == 'ERROR' or entry['long'] == 'ERROR':
            return False
        has_utc = all(entry.get(k) not in ('', None) for k in ['utc_year', 'utc_month', 'utc_day', 'utc_hour', 'utc_min'])
        if not has_utc and entry['timestamp_time'] == 'ERROR':
            return False
        return True

class OnStarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OnStar GPS Decoder")
        self.root.geometry("800x600")
        self.root.configure(bg='#1a1a1a')

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('Title.TLabel', 
                           background='#1a1a1a', 
                           foreground='#ffffff', 
                           font=('Segoe UI', 24, 'bold'))
    
        self.style.configure('Subtitle.TLabel', 
                           background='#1a1a1a', 
                           foreground='#cccccc', 
                           font=('Segoe UI', 11))
    
        self.style.configure('Dark.TFrame', 
                           background='#1a1a1a', 
                           relief='flat')
    
        self.style.configure('DropZone.TFrame', 
                           background='#252525',
                           relief='solid', 
                           borderwidth=1,
                           bordercolor='#333333')
    
        self.style.configure('Dark.TButton',
                           background='#4a9eff',
                           foreground='white',
                           font=('Segoe UI', 10),
                           borderwidth=0,
                           focuscolor='none')
    
        self.style.map('Dark.TButton',
                      background=[('active', '#3d8ce6'),
                                ('pressed', '#2d7acc')])
        
        self.style.configure('Disabled.TButton',
            background='#888888',
            foreground='#cccccc',
            font=('Segoe UI', 10),
            borderwidth=0,
            focuscolor='none'
        )
        self.style.map('Disabled.TButton',
            background=[('active', '#888888'), ('disabled', '#888888')],
            foreground=[('disabled', '#cccccc')]
        )
    
        self.style.configure('Progress.TProgressbar',
                           background='#4a9eff',
                           troughcolor='#333333',
                           borderwidth=0,
                           lightcolor='#4a9eff',
                           darkcolor='#4a9eff')
    
        self.style.configure('Horizontal.TProgressbar',
                           background='#4a9eff',
                           troughcolor='#333333',
                           borderwidth=0,
                           lightcolor='#4a9eff',
                           darkcolor='#4a9eff')

        self.decoder = OnStarDecoder()
        self.input_file = None
        self.is_processing = False

        self.setup_ui()
        self.setup_drag_drop()

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=40, pady=30)
    
        # Header
        header_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        header_frame.pack(fill='x', pady=(0, 30))
    
        title_label = ttk.Label(header_frame, text="OnStar GPS Decoder", style='Title.TLabel')
        title_label.pack(anchor='w')
    
        subtitle_label = ttk.Label(header_frame, 
                                 text="Extract and decode GPS data from OnStar binary files", 
                                 style='Subtitle.TLabel')
        subtitle_label.pack(anchor='w', pady=(5, 0))
    
        # Drop zone
        self.drop_frame = ttk.Frame(main_frame, style='DropZone.TFrame')
        self.drop_frame.pack(fill='both', expand=True, pady=(0, 20))
    
        # Use tk.Frame for drop_content to control background precisely
        drop_content = tk.Frame(self.drop_frame, bg='#252525')
        drop_content.place(relx=0.5, rely=0.5, anchor='center')
    
        # Drop zone icon (load a proper PNG with transparency)
        try:
            self.icon_image = tk.PhotoImage(file="folder_icon.png")
            icon_label = tk.Label(drop_content, image=self.icon_image, bg='#252525')
        except tk.TclError:
            # Fallback to text if the image fails to load
            icon_label = tk.Label(drop_content, text="📁", bg='#252525', fg='#4a9eff', font=('Segoe UI', 48))
        icon_label.pack(pady=(0, 10))
    
        self.drop_label = tk.Label(
            drop_content,
            text="Drop OnStar binary file here\nor click to browse",
            bg='#252525',
            fg='#cccccc',
            font=('Segoe UI', 14),
            justify='center'
        )
        self.drop_label.pack()
    
        # File info
        self.file_info_label = tk.Label(
            drop_content,
            text="",
            bg='#252525',
            fg='#888888',
            font=('Segoe UI', 10)
        )
        self.file_info_label.pack(pady=(10, 0))
    
        # Buttons frame
        button_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(0, 20))
    
        # Browse button
        self.browse_btn = ttk.Button(button_frame, text="Browse Files", 
            style='Dark.TButton',
            command=self.browse_file
        )
        self.browse_btn.pack(side='left', padx=(0, 10))
    
        # Process button (start as disabled and gray)
        self.process_btn = ttk.Button(button_frame, text="Process File", 
            style='Disabled.TButton',
            command=self.process_file,
            state='disabled'
        )
        self.process_btn.pack(side='left')
    
        # Clear button (start as disabled and gray)
        self.clear_btn = ttk.Button(button_frame, text="Clear", 
            style='Disabled.TButton',
            command=self.clear_file,
            state='disabled'
        )
        self.clear_btn.pack(side='right')
    
        # Progress section
        progress_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        progress_frame.pack(fill='x')
    
        self.progress_label = ttk.Label(progress_frame, text="",
                                      background='#1a1a1a', 
                                      foreground='#cccccc',
                                      font=('Segoe UI', 10))
        self.progress_label.pack(anchor='w', pady=(0, 5))
    
        self.progress = ttk.Progressbar(progress_frame, style='Horizontal.TProgressbar', mode='determinate', length=300)
        self.progress.pack(fill='x')
    
        # Results section
        results_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        results_frame.pack(fill='x', pady=(20, 0))
    
        self.results_label = ttk.Label(results_frame, text="",
                                     background='#1a1a1a', 
                                     foreground='#4a9eff',
                                     font=('Segoe UI', 11, 'bold'))
        self.results_label.pack(anchor='w')
    
    def setup_drag_drop(self):
        # Bind click event to drop zone
        self.drop_frame.bind("<Button-1>", lambda e: self.browse_file())
        self.drop_label.bind("<Button-1>", lambda e: self.browse_file())

        # Enable drag-and-drop for files
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.on_file_drop)
    
    def browse_file(self):
        if self.is_processing:
            return
            
        file_path = filedialog.askopenfilename(
            title="Select OnStar Binary File",
            filetypes=[
                ("CE0 files", "*.CE0*"),
                ("All files", "*.*"),
            ]
        )
        
        if file_path:
            self.set_input_file(file_path)
    
    def set_input_file(self, file_path):
        self.input_file = file_path
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        size_mb = file_size / (1024 * 1024)
        
        self.drop_label.configure(text=f"Selected: {filename}")
        self.file_info_label.configure(text=f"Size: {size_mb:.2f} MB")
        self.process_btn.configure(state='normal', style='Dark.TButton')
        self.clear_btn.configure(state='normal', style='Dark.TButton')
    
    def clear_file(self):
        if self.is_processing:
            return

        self.input_file = None
        self.drop_label.configure(text="Drop OnStar binary file here\nor click to browse")
        self.file_info_label.configure(text="")
        self.process_btn.configure(state='disabled', style='Disabled.TButton')
        self.progress_label.configure(text="")
        self.progress['value'] = 0
        self.results_label.configure(text="")
        self.clear_btn.configure(state='disabled', style='Disabled.TButton')
    
    def process_file(self):
        if not self.input_file or self.is_processing:
            return
        
        self.is_processing = True
        self.process_btn.configure(state='disabled', text='Processing...')
        self.browse_btn.configure(state='disabled')
        self.clear_btn.configure(state='disabled')
        
        # Generate output path
        base, _ = os.path.splitext(self.input_file)
        output_path = base + ".xlsx"
        
        # Start processing in a separate thread
        thread = threading.Thread(target=self.process_in_background, 
                                args=(self.input_file, output_path))
        thread.daemon = True
        thread.start()
    
    def process_in_background(self, input_path, output_path):
        def progress_callback(status, percent):
            self.root.after(0, self.update_progress, status, percent)
    
        try:
            entry_count, result = self.decoder.extract_gps_data(
                input_path, output_path, progress_callback
            )
        
            # Check if result is None before calling startswith
            if isinstance(result, str) and (result.startswith("Error") or result.startswith("File not found")):
                self.root.after(0, self.processing_error, result)
            else:
                self.root.after(0, self.processing_complete, entry_count, output_path)
            
        except Exception as e:
            self.root.after(0, self.processing_error, str(e))
    
    def update_progress(self, status, percent):
        self.progress_label.configure(text=status)
        self.progress['value'] = percent
        self.root.update_idletasks()
    
    def processing_complete(self, entry_count, output_path):
        self.is_processing = False
        self.process_btn.configure(state='normal', text='Process File', style='Dark.TButton')
        self.browse_btn.configure(state='normal')
        self.clear_btn.configure(state='normal', style='Dark.TButton')
    
        self.progress_label.configure(text="Processing complete!")
        self.progress['value'] = 100
    
        xlsx_filename = os.path.basename(output_path)
        result_text = f"✓ Successfully extracted {entry_count} GPS entries to:\n  - XLSX: {xlsx_filename}"
    
        self.results_label.configure(text=result_text)
    
    def processing_error(self, error_msg):
        self.is_processing = False
        self.process_btn.configure(state='normal', text='Process File')
        self.browse_btn.configure(state='normal')
        self.clear_btn.configure(state='normal')
    
        self.progress_label.configure(text="Processing failed!")
        self.progress['value'] = 0
        self.results_label.configure(text=f"✗ Error: {error_msg}")
    
        messagebox.showerror("Processing Error", f"Failed to process file:\n\n{error_msg}")

    def on_file_drop(self, event):
        if self.is_processing:
            return
        # event.data may contain a list of files; take the first one
        file_path = event.data.strip().split()[0]
        if os.path.isfile(file_path):
            self.set_input_file(file_path)


def main():
    root = TkinterDnD.Tk()  # Use TkinterDnD for drag-and-drop support
    icon_path_for_display = "car.ico" # Used for a more user-friendly message

    try:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPass'):
            # Application is frozen (bundled by PyInstaller)
            # sys._MEIPass is the path to the temporary folder where bundled files are extracted
            base_path = sys._MEIPass
            icon_path = os.path.join(base_path, "car.ico")
            icon_path_for_display = icon_path # Show full path in case of error for bundled app
        else:
            # Application is running in a normal Python environment (development)
            # Icon is expected to be in the same directory as the script
            base_path = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_path, "car.ico")
            icon_path_for_display = icon_path # Show full path in case of error for dev

        # For debugging, you can uncomment these lines to check if the file exists
        # if not os.path.exists(icon_path):
        #     print(f"DEBUG: Icon file does NOT exist at: {icon_path}")
        # else:
        #     print(f"DEBUG: Icon file found at: {icon_path}")

        root.iconbitmap(icon_path)

    except tk.TclError as e:
        # Construct a more detailed error message
        error_details = (
            f"Could not load the icon file '{os.path.basename(icon_path_for_display)}'. Using default.\n\n"
            f"Attempted path: {icon_path_for_display}\n"
            f"Error: {e}"
        )
        print(f"ICON LOAD ERROR: {error_details}") # Print to console if available
        messagebox.showwarning("Icon Error", error_details)
        
    app = OnStarGUI(root) # Initialize your application GUI
    
    # Center the window
    # The OnStarGUI class already sets the initial geometry (e.g., "800x600")
    root.update_idletasks() # Ensure window dimensions are updated
    
    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Get window dimensions
    window_width = root.winfo_width()
    window_height = root.winfo_height()
    
    # Calculate position for centering
    position_x = (screen_width // 2) - (window_width // 2)
    position_y = (screen_height // 2) - (window_height // 2)
    
    # Set the window's position (size is already set by OnStarGUI)
    root.geometry(f"+{position_x}+{position_y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()