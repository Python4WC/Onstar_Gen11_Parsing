import binascii
import re
import struct
from datetime import datetime, timezone
import csv
import sys
import os

class OnStarDecoder:
    def __init__(self):
        # GPS epoch start: January 6, 1980 00:00:00 UTC (first Sunday of 1980)
        self.gps_epoch = datetime(1980, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
    
    def extract_gps_data(self, file_path, output_csv_path):
        """Extract GPS data from OnStar binary file and decode it to CSV"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Find GPS data blocks in the binary data
            gps_blocks = self.find_gps_blocks_binary(data)
            
            # Parse each block into individual entries
            parsed_entries = []
            for block in gps_blocks:
                entry = self.parse_gps_block(block)
                if entry and self.is_valid_entry(entry):
                    parsed_entries.append(entry)
            
            # Write to CSV
            self.write_csv(parsed_entries, output_csv_path)
            
            print(f"Found {len(parsed_entries)} valid GPS entries.")
            print(f"Results written to: {output_csv_path}")
                
        except FileNotFoundError:
            print(f"Error: File not found - {file_path}")
        except Exception as e:
            print(f"Error processing file: {e}")
    
    def find_gps_blocks_binary(self, data):
        """Find GPS data blocks in binary data"""
        blocks = []
        
        # Convert to string but preserve structure by using latin-1 encoding
        # This preserves all byte values while allowing string operations
        text_data = data.decode('latin-1', errors='ignore')
        
        # Look for GPS keywords and extract surrounding context
        gps_patterns = [
            b'gps_tow=',
            b'gps_week=', 
            b'utc_year=',
            b'lat=',
            b'lon='
        ]
        
        # Find all GPS keyword positions
        keyword_positions = []
        for pattern in gps_patterns:
            pattern_str = pattern.decode('latin-1')
            for match in re.finditer(re.escape(pattern_str), text_data):
                keyword_positions.append(match.start())
        
        if not keyword_positions:
            return blocks
            
        keyword_positions.sort()
        
        # Group nearby keywords into blocks
        i = 0
        while i < len(keyword_positions):
            block_start = keyword_positions[i]
            block_end = block_start + 200  # Start with a reasonable block size
            
            # Extend block to include nearby keywords
            j = i + 1
            while j < len(keyword_positions) and keyword_positions[j] - block_start < 1000:
                block_end = max(block_end, keyword_positions[j] + 200)
                j += 1
            
            # Extract block with some padding
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
            # Extract GPS time components with more flexible patterns
            gps_tow = self.extract_number_flexible(block_text, [r'gps_tow=(\d+)', r'tow=(\d+)'])
            gps_week = self.extract_number_flexible(block_text, [r'gps_week=(\d+)', r'week=(\d+)'])
            
            # Extract UTC components with flexible patterns
            utc_year = self.extract_number_flexible(block_text, [r'utc_year=(\d+)', r'year=(\d{4})'])
            utc_month = self.extract_number_flexible(block_text, [r'utc_month=(\d+)', r'month=(\d+)'])
            utc_day = self.extract_number_flexible(block_text, [r'utc_day=(\d+)', r'day=(\d+)'])
            utc_hour = self.extract_number_flexible(block_text, [r'utc_hour=(\d+)', r'hour=(\d+)'])
            utc_min = self.extract_number_flexible(block_text, [r'utc_min=(\d+)', r'min=(\d+)'])
            
            # Store UTC breakdown in entry
            entry['utc_year'] = utc_year if utc_year is not None else ''
            entry['utc_month'] = utc_month if utc_month is not None else ''
            entry['utc_day'] = utc_day if utc_day is not None else ''
            entry['utc_hour'] = utc_hour if utc_hour is not None else ''
            entry['utc_min'] = utc_min if utc_min is not None else ''
            
            # Extract coordinates with more flexible hex patterns
            lat_hex = self.extract_hex_flexible(block_text, [r'lat=([0-9A-Fa-f]{16})', r'lat=([0-9A-Fa-f\s]{16,})'])
            lon_hex = self.extract_hex_flexible(block_text, [r'lon=([0-9A-Fa-f]{16})', r'lon=([0-9A-Fa-f\s]{16,})'])
            
            # Store original hex values
            entry['lat_hex'] = lat_hex if lat_hex else ''
            entry['lon_hex'] = lon_hex if lon_hex else ''
            
            # Process GPS timestamp  
            if gps_tow is not None and gps_week is not None:
                try:
                    # Validate GPS values
                    if 0 <= gps_tow <= 604800000 and 0 <= gps_week <= 4000:  # Reasonable ranges
                        gps_tow_sec = gps_tow / 1000.0
                        gps_week_sec = gps_week * 604800
                        total_seconds = gps_week_sec + gps_tow_sec
                        gps_timestamp = self.gps_epoch.timestamp() + total_seconds
                        dt = datetime.fromtimestamp(gps_timestamp, tz=timezone.utc)
                        entry['timestamp_time'] = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # milliseconds
                except Exception as e:
                    print(f"GPS timestamp conversion error: {e}")
            
            # Process coordinates
            if lat_hex:
                try:
                    # Clean hex string
                    clean_hex = re.sub(r'[^0-9A-Fa-f]', '', lat_hex)
                    if len(clean_hex) == 16:
                        lat_bytes = bytes.fromhex(clean_hex)
                        lat_raw = struct.unpack('<d', lat_bytes)[0]  # little-endian double
                        lat_decimal = lat_raw / 10000000.0
                        # Validate latitude range
                        if -90 <= lat_decimal <= 90:
                            entry['lat'] = lat_decimal
                        else:
                            print(f"Invalid latitude: {lat_decimal}")
                except Exception as e:
                    print(f"Latitude conversion error: {e}")
                    entry['lat'] = 'ERROR'
            
            if lon_hex:
                try:
                    # Clean hex string
                    clean_hex = re.sub(r'[^0-9A-Fa-f]', '', lon_hex)
                    if len(clean_hex) == 16:
                        lon_bytes = bytes.fromhex(clean_hex)
                        lon_raw = struct.unpack('<d', lon_bytes)[0]  # little-endian double  
                        lon_decimal = lon_raw / 10000000.0
                        # Validate longitude range
                        if -180 <= lon_decimal <= 180:
                            entry['long'] = lon_decimal
                        else:
                            print(f"Invalid longitude: {lon_decimal}")
                except Exception as e:
                    print(f"Longitude conversion error: {e}")
                    entry['long'] = 'ERROR'
            
            return entry
                
        except Exception as e:
            print(f"Error parsing GPS block: {e}")
            
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
                # Clean up hex value
                clean_hex = re.sub(r'[^0-9A-Fa-f]', '', hex_val)
                if len(clean_hex) >= 16:
                    return clean_hex[:16]  # Take first 16 hex chars
        return None
    
    def is_valid_entry(self, entry):
        """Check if entry has at least some valid data"""
        if not entry:
            return False
        
        # Must have coordinates
        if entry['lat'] == 'ERROR' or entry['long'] == 'ERROR':
            return False
            
        # Must have at least one time field (either timestamp_time or all UTC fields present)
        has_utc = all(entry.get(k) not in ('', None) for k in ['utc_year', 'utc_month', 'utc_day', 'utc_hour', 'utc_min'])
        if not has_utc and entry['timestamp_time'] == 'ERROR':
            return False
            
        return True
    
    def write_csv(self, entries, output_path):
        """Write entries to CSV file"""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'lat', 'long',
                    'utc_year', 'utc_month', 'utc_day', 'utc_hour', 'utc_min',
                    'timestamp_time',
                    '', '', '', '', '', '',
                    'lat_hex', 'lon_hex'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for entry in entries:
                    # Replace blank UTC fields with "ERROR"
                    for utc_field in ['utc_year', 'utc_month', 'utc_day', 'utc_hour', 'utc_min']:
                        if not entry.get(utc_field):
                            entry[utc_field] = 'ERROR'
                    # Check if timestamp_time is a valid date and before 2010
                    ts = entry.get('timestamp_time', '')
                    if ts and ts != 'ERROR':
                        try:
                            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
                            if dt.year < 2010:
                                entry['timestamp_time'] = 'INVALID PRE-2010 DATE'
                        except Exception:
                            pass
                    # Add six blank columns
                    for i in range(1, 7):
                        entry[f'blank{i}'] = ''
                    writer.writerow({
                        'lat': entry.get('lat', ''),
                        'long': entry.get('long', ''),
                        'utc_year': entry.get('utc_year', ''),
                        'utc_month': entry.get('utc_month', ''),
                        'utc_day': entry.get('utc_day', ''),
                        'utc_hour': entry.get('utc_hour', ''),
                        'utc_min': entry.get('utc_min', ''),
                        'timestamp_time': entry.get('timestamp_time', ''),
                        '': '',
                        '': '',
                        '': '',
                        '': '',
                        '': '',
                        '': '',
                        'lat_hex': entry.get('lat_hex', ''),
                        'lon_hex': entry.get('lon_hex', '')
                    })
                # Write two blank lines
                csvfile.write('\n\n')
                # Write the custom line
                csvfile.write('Script Created by Steven Schiavone\n')
        except Exception as e:
            print(f"Error writing CSV: {e}")

def main():
    input_file = input("Enter the path to the input file: ").strip()
    if not os.path.isfile(input_file):
        print(f"Error: File not found - {input_file}")
        return

    base, _ = os.path.splitext(input_file)
    output_file = base + ".csv"

    decoder = OnStarDecoder()
    decoder.extract_gps_data(input_file, output_file)

if __name__ == "__main__":
    main()