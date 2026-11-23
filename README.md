# AE Project Downgrader Toolkit

Tools for downgrading After Effects projects (.aep) to older versions.

| What it does | What it does NOT do |
|-------------|---------------------|
| Changes version header so older AE *tries* to open file | Convert new effects to old equivalents |
| Preserves all composition data, keyframes, expressions | Fix expressions using new syntax |
| Works on binary .aep directly (no .aepx needed) | Handle 3D layers, VR, Cineware, new features |
| Fast, no AE installation required | Guarantee project will work |

**Results vary wildly:**
- ✅ Simple projects (footage, solids, basic effects): Often work
- ⚠️ Expressions: May error if using new syntax
- ⚠️ New effects (e.g., Advanced Puppet, Content-Aware Fill): Will be missing
- ❌ 3D/Cinema 4D/VR: Will likely crash or lose data
- ❌ Plugin dependencies: Must have same plugins installed

**ALWAYS TEST ON A COPY!**

---

## Tools Included

### 1. `aep_binary_downgrader.py` - Main Binary Patcher
Patches the RIFX header version chunk

```bash
# Analyze a file first
python aep_binary_downgrader.py analyze project.aep

# Dry run - see what would change
python aep_binary_downgrader.py patch project.aep -t 2023 --dry-run

# Actually patch
python aep_binary_downgrader.py patch project.aep -t 2023 -o project_2023.aep

# Batch process folder
python aep_binary_downgrader.py batch ./projects ./output -t 2023
```

**Supported target versions:** 2025, 2024, 2023, 2022, 2021, 2020, 2019

### 2. `aepx-analyzer.py` - XML Project Analyzer
For .aepx files (XML format). Use to check compatibility before downgrading.

```bash
python aepx-analyzer.py project.aepx -t 2023
python aepx-analyzer.py ./folder -t 2023
```

### 3. `batch-downgrade.jsx` - After Effects Script
Run **inside newer AE** (2024/2025) to properly "Save As Previous Version" - the only 100% reliable method.

```javascript
// In AE: File > Scripts > Run Script File... > batch-downgrade.jsx
```

---


## How the Binary Patcher Works

After Effects .aep files use a **RIFX** (little-endian RIFF) container format:

```
RIFX header (12 bytes)
  ├── "RIFX" (4 bytes)
  ├── file size (4 bytes)
  └── "AEP " (4 bytes)
Chunks:
  ├── "ver " chunk → version string (e.g., "24.0")
  ├── "bld " chunk → build number (e.g., "24.6.2.2")
  └── ... project data ...
```

The patcher:
1. Finds the RIFX header
2. Locates the `ver ` chunk with version string
3. Replaces version bytes (e.g., "24.0" → "23.0")
4. Optionally patches build number
5. Writes new file

**No project data is modified** - only the version identification header.

---


## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "Unrecognized file format" | Header patch failed / wrong offset | Try different target version |
| Crashes on open | Incompatible feature (3D, VR, new effect) | Remove feature in newer AE first |
| "Missing effect" warnings | Effect doesn't exist in target AE | Replace with equivalent or ignore |
| Expression errors | New JS syntax (optional chaining, etc.) | Rewrite expressions manually |
| Font missing | Font not installed | Install font or replace |

---


---

## License

MIT - Use at your own risk. Always backup your projects!