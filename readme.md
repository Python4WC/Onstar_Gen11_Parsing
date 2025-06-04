# OnStar (v10+) GPS Data Decoder

A Python tool for extracting and decoding GPS data from OnStar binary files, converting the data into structured CSV format for analysis.

## Overview

The OnStar Decoder processes binary files containing GPS telemetry data from OnStar systems, extracting location coordinates and timestamps. The tool handles various data formats and performs validation to ensure data integrity.

## Features

- **Binary Data Processing**: Reads and parses OnStar binary files containing GPS data
- **GPS Time Conversion**: Converts GPS week/time-of-week to UTC timestamps
- **Coordinate Decoding**: Extracts and converts hexadecimal coordinate data to decimal degrees
- **Data Validation**: Validates GPS coordinates and timestamps for accuracy
- **CSV Export**: Outputs structured data in CSV format for further analysis
- **Error Handling**: Robust error handling with detailed logging

## Installation

### Requirements
- Python 3.6+
- Standard library modules (no external dependencies)

### Dependencies
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

## CLI Usage

### Command Line Interface
```bash
python onstar_decoder.py
```

The program will prompt for the input file path and automatically generate a CSV output file with the same base name.

### Programmatic Usage
```python
from onstar_decoder import OnStarDecoder

decoder = OnStarDecoder()
decoder.extract_gps_data('input_file.bin', 'output_file.csv')
```

## Class Documentation

### `OnStarDecoder`

Main class for processing OnStar GPS data files.

#### Constructor
```python
def __init__(self):
```
Initializes the decoder with GPS epoch reference (January 6, 1980 00:00:00 UTC).

#### Methods

##### `extract_gps_data(file_path, output_csv_path)`
Main entry point for GPS data extraction.

**Parameters:**
- `file_path` (str): Path to input binary file
- `output_csv_path` (str): Path for output CSV file

**Process:**
1. Reads binary file data
2. Identifies GPS data blocks
3. Parses individual GPS entries
4. Validates data integrity
5. Exports to CSV format

##### `find_gps_blocks_binary(data)`
Locates GPS data blocks within binary data.

**Parameters:**
- `data` (bytes): Raw binary data from file

**Returns:**
- `list`: Text blocks containing GPS data

**Search Patterns:**
- `gps_tow=` - GPS Time of Week
- `gps_week=` - GPS Week Number
- `utc_year=` - UTC Year
- `lat=` - Latitude data
- `lon=` - Longitude data

##### `parse_gps_block(block_text)`
Parses individual GPS data blocks into structured entries.

**Parameters:**
- `block_text` (str): Text block containing GPS data

**Returns:**
- `dict`: Parsed GPS entry with the following fields:
  - `lat`: Latitude in decimal degrees
  - `long`: Longitude in decimal degrees
  - `utc_year`: Year component
  - `utc_month`: Month component
  - `utc_day`: Day component
  - `utc_hour`: Hour component
  - `utc_min`: Minute component
  - `timestamp_time`: Formatted timestamp string
  - `lat_hex`: Original latitude hex value
  - `lon_hex`: Original longitude hex value

##### `extract_number_flexible(text, patterns)`
Extracts numeric values using multiple regex patterns for flexibility.

**Parameters:**
- `text` (str): Text to search
- `patterns` (list): List of regex patterns to try

**Returns:**
- `int` or `None`: Extracted number or None if not found

##### `extract_hex_flexible(text, patterns)`
Extracts hexadecimal values using multiple regex patterns.

**Parameters:**
- `text` (str): Text to search
- `patterns` (list): List of regex patterns to try

**Returns:**
- `str` or `None`: Cleaned hex string (16 characters) or None

##### `is_valid_entry(entry)`
Validates GPS entries for completeness and accuracy.

**Parameters:**
- `entry` (dict): GPS entry to validate

**Returns:**
- `bool`: True if entry is valid

**Validation Criteria:**
- Must have valid latitude and longitude coordinates
- Must have either complete UTC time components or valid GPS timestamp
- Coordinates must be within valid ranges (-90 to 90° for latitude, -180 to 180° for longitude)

##### `write_csv(entries, output_path)`
Writes validated GPS entries to CSV file.

**Parameters:**
- `entries` (list): List of GPS entry dictionaries
- `output_path` (str): Output CSV file path

## Data Processing Details

### GPS Time Conversion
The decoder converts GPS time to UTC using the following process:

1. **GPS Epoch**: January 6, 1980 00:00:00 UTC (first Sunday of 1980)
2. **GPS Week**: Number of weeks since GPS epoch
3. **Time of Week (TOW)**: Milliseconds since start of current GPS week
4. **Conversion Formula**: 
   ```
   UTC = GPS_EPOCH + (GPS_WEEK × 604800) + (GPS_TOW ÷ 1000)
   ```

### Coordinate Decoding
Coordinates are stored as 16-character hexadecimal strings representing 64-bit doubles:

1. **Hex Cleaning**: Remove non-hex characters
2. **Binary Conversion**: Convert hex to bytes
3. **Struct Unpacking**: Unpack as little-endian double (`<d`)
4. **Scaling**: Divide by 10,000,000 to get decimal degrees

### Data Validation
The system implements multiple validation layers:

- **Range Validation**: Coordinates within Earth's bounds
- **GPS Time Validation**: Reasonable GPS week/TOW values
- **Timestamp Validation**: Dates after 2010 (prevents invalid early dates)
- **Data Completeness**: Required fields present

## GUI Usage



## Output Format

### CSV Structure
The output CSV contains the following columns:

| Column | Description | Type |
|--------|-------------|------|
| lat | Latitude in decimal degrees | float |
| long | Longitude in decimal degrees | float |
| utc_year | UTC year component | int |
| utc_month | UTC month component | int |
| utc_day | UTC day component | int |
| utc_hour | UTC hour component | int |
| utc_min | UTC minute component | int |
| timestamp_time | Formatted timestamp (YYYY-MM-DD HH:MM:SS.mmm) | string |
| (6 blank columns) | Reserved for future use | empty |
| lat_hex | Original latitude hex value | string |
| lon_hex | Original longitude hex value | string |

### Error Handling
Invalid or missing data is marked as "ERROR" in the respective fields.

## Example Usage

```python
# Create decoder instance
decoder = OnStarDecoder()

# Process a binary file
input_file = "onstar_data.bin"
output_file = "gps_data.csv"

try:
    decoder.extract_gps_data(input_file, output_file)
    print("GPS data extraction completed successfully")
except Exception as e:
    print(f"Error processing file: {e}")
```

## Limitations

- Designed specifically for OnStar binary data format
- Requires specific GPS data patterns in the binary file
- Limited to GPS coordinates and basic timestamp information
- No support for additional telemetry data that may be present

## Troubleshooting

### Common Issues

1. **File Not Found**: Ensure the input file path is correct
2. **No GPS Data Found**: Verify the binary file contains OnStar GPS data
3. **Invalid Coordinates**: Check if the coordinate hex values are properly formatted
4. **Timestamp Errors**: GPS time values may be outside expected ranges

### Debug Information
The tool provides console output for:
- Number of valid GPS entries found
- Coordinate conversion errors
- GPS timestamp conversion errors
- File processing status

## Technical Notes

- Uses `latin-1` encoding to preserve binary data integrity during text processing
- Implements flexible regex patterns to handle format variations
- GPS epoch calculation accounts for leap seconds through standard GPS time conversion
- Little-endian byte order assumed for coordinate decoding