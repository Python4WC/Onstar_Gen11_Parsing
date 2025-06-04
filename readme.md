# OnStar (v10+) GPS Data Decoder

A Python tool for extracting and decoding GPS data from OnStar binary files, converting it into structured CSV format for analysis.

## Overview

The OnStar Decoder processes binary files containing GPS telemetry data from OnStar systems (v10+), extracting location coordinates and timestamps. It supports both command-line (CLI) and graphical user interface (GUI) workflows, with robust error handling and data validation.

## Features

- **Binary Data Processing**: Parses OnStar binary files to extract GPS data.
- **GPS Time Conversion**: Converts GPS week and time-of-week to UTC timestamps.
- **Coordinate Decoding**: Converts hexadecimal coordinates to decimal degrees.
- **Data Validation**: Ensures GPS coordinates and timestamps are accurate.
- **CSV Export**: Outputs structured data to CSV for analysis.
- **GUI Support**: Provides a modern, drag-and-drop interface for ease of use.
- **Error Handling**: Includes detailed logging and user-friendly error messages.

## Installation

### Requirements
- Python 3.6+
- No external dependencies (uses standard library modules)

### Dependencies
The following Python standard library modules are used:
```python
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
import csv
from tkinterdnd2 import DND_FILES, TkinterDnD
import platform
```

## Usage

### CLI Usage
Run the decoder from the command line:
```bash
python onstar_decoder.py
```
The program prompts for an input file path and generates a CSV output file with the same base name in the same directory.

#### Programmatic Usage
```python
from onstar_decoder import OnStarDecoder

decoder = OnStarDecoder()
decoder.extract_gps_data("input_file.bin", "output_file.csv")
```

### GUI Usage
The GUI provides a user-friendly interface for processing OnStar binary files.

#### Launching the GUI
```bash
python onstar_gen11-gui.py
```

#### Features
- **Drag-and-Drop**: Drop `.CE0` or other OnStar binary files onto the window.
- **File Browser**: Select files via a file dialog using the "Browse Files" button.
- **Progress Feedback**: Displays real-time progress and status updates.
- **Error Handling**: Shows descriptive error messages for issues like invalid files.
- **Custom UI**: Features a modern, dark-themed interface with rounded corners (Windows) and a responsive layout.
- **Batch Processing**: Extracts all valid GPS entries and exports to CSV.

#### Workflow
1. Launch the GUI: `python onstar_gen11-gui.py`.
2. Select a file by dragging it onto the drop zone or clicking "Browse Files."
3. Review the file name and size displayed in the interface.
4. Click "Process File" to extract GPS data; monitor progress via the progress bar.
5. View results, including the number of GPS entries and the output CSV filename.
6. Click "Clear" to reset and process another file.

#### Output
- The CSV file is saved in the same directory as the input file (e.g., `input.CE0` → `input.csv`).
- Invalid or missing data fields are marked as "ERROR."

#### Platform Notes
- **Windows**: Includes rounded corners and a custom title bar.
- **Other OS**: Uses standard window decorations.

## Output Format

### CSV Structure
The output CSV includes the following columns:

| Column          | Description                              | Type   |
|-----------------|------------------------------------------|--------|
| `lat`           | Latitude in decimal degrees              | float  |
| `long`          | Longitude in decimal degrees             | float  |
| `utc_year`      | UTC year component                      | int    |
| `utc_month`     | UTC month component                     | int    |
| `utc_day`       | UTC day component                       | int    |
| `utc_hour`      | UTC hour component                      | int    |
| `utc_min`       | UTC minute component                    | int    |
| `timestamp_time`| Formatted timestamp (YYYY-MM-DD HH:MM:SS.mmm) | string |
| (6 blank columns)| Reserved for future use                 | empty  |
| `lat_hex`       | Original latitude hex value             | string |
| `lon_hex`       | Original longitude hex value            | string |

## Class Documentation

### `OnStarDecoder`
Main class for processing OnStar GPS data files.

#### Constructor
```python
def __init__(self):
```
Initializes the decoder with the GPS epoch (January 6, 1980, 00:00:00 UTC).

#### Methods
- **`extract_gps_data(file_path, output_csv_path)`**  
  Extracts GPS data from a binary file and saves it to a CSV file.  
  - **Parameters**: `file_path` (str), `output_csv_path` (str)  
  - **Process**: Reads file, identifies GPS blocks, parses entries, validates data, and exports to CSV.

- **`find_gps_blocks_binary(data)`**  
  Locates GPS data blocks in binary data.  
  - **Parameters**: `data` (bytes)  
  - **Returns**: List of text blocks with GPS data.  
  - **Patterns**: Searches for `gps_tow=`, `gps_week=`, `utc_year=`, `lat=`, `lon=`.

- **`parse_gps_block(block_text)`**  
  Parses a GPS data block into a structured entry.  
  - **Parameters**: `block_text` (str)  
  - **Returns**: Dictionary with `lat`, `long`, `utc_year`, `utc_month`, `utc_day`, `utc_hour`, `utc_min`, `timestamp_time`, `lat_hex`, `lon_hex`.

- **`extract_number_flexible(text, patterns)`**  
  Extracts numeric values using regex patterns.  
  - **Parameters**: `text` (str), `patterns` (list)  
  - **Returns**: `int` or `None`.

- **`extract_hex_flexible(text, patterns)`**  
  Extracts 16-character hexadecimal values.  
  - **Parameters**: `text` (str), `patterns` (list)  
  - **Returns**: `str` or `None`.

- **`is_valid_entry(entry)`**  
  Validates GPS entries.  
  - **Parameters**: `entry` (dict)  
  - **Returns**: `bool`  
  - **Criteria**: Valid latitude (-90 to 90°), longitude (-180 to 180°), and timestamps (post-2010).

- **`write_csv(entries, output_path)`**  
  Writes GPS entries to a CSV file.  
  - **Parameters**: `entries` (list), `output_path` (str)

## Technical Details

### GPS Time Conversion
Converts GPS time to UTC:
- **GPS Epoch**: January 6, 1980, 00:00:00 UTC
- **Formula**: `UTC = GPS_EPOCH + (GPS_WEEK × 604800) + (GPS_TOW ÷ 1000)`
- Accounts for leap seconds via standard GPS time conversion.

### Coordinate Decoding
- **Input**: 16-character hexadecimal strings (64-bit doubles).
- **Process**: Clean hex, convert to bytes, unpack as little-endian double (`<d`), divide by 10,000,000 for decimal degrees.

### Data Validation
- **Range**: Latitude (-90 to 90°), longitude (-180 to 180°).
- **Timestamp**: Dates after 2010, valid GPS week/TOW.
- **Completeness**: Ensures required fields are present.

## Example Usage
```python
from onstar_decoder import OnStarDecoder

decoder = OnStarDecoder()
input_file = "onstar_data.bin"
output_file = "gps_data.csv"

try:
    decoder.extract_gps_data(input_file, output_file)
    print("GPS data extraction completed successfully")
except Exception as e:
    print(f"Error processing file: {e}")
```

## Limitations
- Specific to OnStar binary data format.
- Requires `gps_tow=`, `gps_week=`, `lat=`, and `lon=` patterns.
- Limited to GPS coordinates and timestamps; no additional telemetry.
- Assumes little-endian byte order for coordinates.

## Troubleshooting
- **File Not Found**: Verify the input file path.
- **No GPS Data**: Ensure the file contains OnStar GPS data.
- **Invalid Coordinates**: Check hex format of coordinates.
- **Timestamp Errors**: Confirm GPS week/TOW values are reasonable.

### Debug Output
- Number of valid GPS entries.
- Coordinate and timestamp conversion errors.
- File processing status.

## Technical Notes
- Uses `latin-1` encoding to preserve binary data.
- Flexible regex patterns handle format variations.
- Little-endian byte order for coordinate decoding.