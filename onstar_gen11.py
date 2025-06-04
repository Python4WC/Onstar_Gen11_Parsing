import binascii
import re
import struct
from datetime import datetime

def extract_and_search_hex(file_path):
    # Read the file as binary
    with open(file_path, 'rb') as f:
        data = f.read()
    hex_data = binascii.hexlify(data).decode('ascii')

def extract_and_dump_plaintext(file_path, output_txt_path):
    # Read the file as binary
    with open(file_path, 'rb') as f:
        data = f.read()
    # Extract ASCII printable strings of length >= 4
    pattern = rb'[\x20-\x7E]{4,}'
    matches = re.findall(pattern, data)
    # Define keywords to match as substrings
    keywords = ['tow', 'week', 'gps', 'utc', 'lat', 'lon']
    keyword_re = re.compile('|'.join(keywords))
    # Regex for hex code (at least 2 hex digits) or a number (int or float)
    hex_or_number_re = re.compile(r'\b([0-9A-Fa-f]{2,}|\d+(\.\d+)?)\b')
    # Write only lines containing any of the keywords AND a hex code or number
    with open(output_txt_path, 'w', encoding='utf-8') as out_f:
        for match in matches:
            line = match.decode('ascii', errors='ignore')
            if keyword_re.search(line) and hex_or_number_re.search(line):
                out_f.write(line + '\n')

if __name__ == "__main__":
    file_path = r"C:\Users\wcdaht\Documents\Onstar\CFL-23-0171.OnStar_NAND.CE0"
    output_txt_path = r"C:\Users\wcdaht\Documents\Onstar\CFL-23-0171.OnStar_NAND.CE0.txt"
    extract_and_dump_plaintext(file_path, output_txt_path)
