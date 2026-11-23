import struct

filepath = r"D:\Project Files Ve Presetler\WHILE ROBBY IS TAKING PHOTOS OF A CAR HE THINKS A WAY OF STEALING THE PASSCODE.aep"

with open(filepath, "rb") as f:
    data = f.read()

print(f"File size: {len(data)}")

# Test find_rifx_egg logic step by step
print("\n--- find_rifx_egg debug ---")
rifx_pos = data.find(b"RIFX")
print(f"data.find(b'RIFX'): {rifx_pos}")

if rifx_pos >= 0:
    print(f"rifx_pos + 12 <= len(data): {rifx_pos + 12 <= len(data)}")
    if rifx_pos + 12 <= len(data):
        form_type = data[rifx_pos + 8:rifx_pos + 12]
        print(f"form_type at rifx_pos+8: {form_type}")
        print(f"form_type == b'Egg!': {form_type == b'Egg!'}")
        if form_type == b"Egg!":
            print(f"Would return: ({rifx_pos}, {rifx_pos + 8})")

# Test find_head_chunk logic
print("\n--- find_head_chunk debug ---")
egg_offset = 8  # from above
search_start = egg_offset + 4
print(f"search_start: {search_start} (0x{search_start:X})")
head_pos = data.find(b"head", search_start)
print(f"data.find(b'head', {search_start}): {head_pos} (0x{head_pos:X})")

if head_pos >= 0:
    print(f"head_pos + 8 <= len(data): {head_pos + 8 <= len(data)}")
    if head_pos + 8 <= len(data):
        chunk_size = struct.unpack("<I", data[head_pos + 4:head_pos + 8])[0]
        print(f"chunk_size (LE): {chunk_size} (0x{chunk_size:X})")
        data_start = head_pos + 8
        data_end = data_start + chunk_size
        print(f"data_start: {data_start}, data_end: {data_end}")
        print(f"data_end <= len(data): {data_end <= len(data)}")

        head_data = data[data_start:data_end]
        print(f"head_data ({len(head_data)} bytes): {head_data.hex()}")
        if len(head_data) >= 8:
            print(f"head_data[0]: 0x{head_data[0]:02X}")
            print(f"head_data[1]: 0x{head_data[1]:02X} (major version byte)")
            print(f"head_data[2:8]: {head_data[2:8].hex()} (signature)")

# Byte to version mapping
BYTE_TO_VERSION = {
    0x60: 2025, 0x5F: 2024, 0x5E: 2023, 0x5D: 2022,
    0x5C: 2021, 0x5B: 2020, 0x5A: 2019, 0x59: 2018
}

if head_pos >= 0 and len(head_data) >= 2:
    major_byte = head_data[1]
    print(f"\nMajor version byte: 0x{major_byte:02X} -> AE {BYTE_TO_VERSION.get(major_byte, 'Unknown')}")