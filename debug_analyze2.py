import struct

filepath = r"D:\Project Files Ve Presetler\WHILE ROBBY IS TAKING PHOTOS OF A CAR HE THINKS A WAY OF STEALING THE PASSCODE.aep"

with open(filepath, "rb") as f:
    data = f.read()

print(f"File size: {len(data)}")

# Test find_rifx_egg logic step by step
rifx_pos = data.find(b"RIFX")
print(f"RIFX pos: {rifx_pos}")

if rifx_pos >= 0:
    form_type = data[rifx_pos + 8:rifx_pos + 12]
    print(f"form_type: {form_type}")
    print(f"is Egg!: {form_type == b'Egg!'}")

egg_offset = rifx_pos + 8
search_start = egg_offset + 4
print(f"search_start: {search_start}")

head_pos = data.find(b"head", search_start)
print(f"head pos: {head_pos}")

if head_pos >= 0:
    chunk_size = struct.unpack("<I", data[head_pos + 4:head_pos + 8])[0]
    print(f"chunk_size: {chunk_size}")
    data_start = head_pos + 8
    head_data = data[data_start:data_start + chunk_size]
    print(f"head_data len: {len(head_data)}")
    if len(head_data) >= 8:
        print(f"head_data[0]: 0x{head_data[0]:02X}")
        print(f"head_data[1]: 0x{head_data[1]:02X}")
        print(f"head_data[2:8]: {head_data[2:8].hex()}")

BYTE_TO_VERSION = {0x60: 2025, 0x5F: 2024, 0x5E: 2023, 0x5D: 2022}
print(f"Version: {BYTE_TO_VERSION.get(head_data[1], 'Unknown')}")