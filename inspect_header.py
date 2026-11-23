import sys

filepath = r"D:\Project Files Ve Presetler\WHILE ROBBY IS TAKING PHOTOS OF A CAR HE THINKS A WAY OF STEALING THE PASSCODE.aep"

with open(filepath, "rb") as f:
    data = f.read(128)

print("First 128 bytes:")
for i in range(0, len(data), 16):
    hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
    print(f'{i:04X}: {hex_str:<48} {ascii_str}')

# Search for known patterns
print("\nSearching for patterns:")
for pattern, name in [(b"RIFX", "RIFX"), (b"RIFF", "RIFF"), (b"Egg!", "Egg!"), (b"head", "head")]:
    pos = data.find(pattern)
    if pos >= 0:
        print(f"  {name}: found at offset 0x{pos:X}")
    else:
        print(f"  {name}: NOT FOUND in first 128 bytes")

# Full search in file
print("\nFull file search (first 1MB)...")
with open(filepath, "rb") as f:
    full = f.read(1024*1024)
    for pattern, name in [(b"RIFX", "RIFX"), (b"RIFF", "RIFF"), (b"Egg!", "Egg!"), (b"head", "head")]:
        pos = full.find(pattern)
        if pos >= 0:
            print(f"  {name}: found at offset 0x{pos:X} ({pos})")
        else:
            print(f"  {name}: NOT FOUND")