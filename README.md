# 🎬 MediaClean

> **A modern GUI tool to filter and clean up media files (Images · Videos · Audio)**

MediaClean is a Desktop application (built with Python + PyQt6) designed to help you easily clean up and manage your media library. It provides 2 main features:

1. **Exact Duplicate Finder**: Detect and remove exact duplicates (files that are 100% identical in content, regardless of their names). It is designed with safety in mind, always keeping at least one original copy.
2. **Same Name, Different Extension Finder**: Easily filter and remove redundant formats (e.g., keep the RAW `.arw` file and delete the accompanying JPEG `.jpg` file).

Notably, the application supports in-app previews for popular image formats as well as **RAW** files (such as ARW, CR2, NEF, etc.).

---

## ⚙️ Installation

### System Requirements
- **Python 3.10+**
- Windows 10/11 (tested)

### Installation Steps

```bash
# 1. Clone or download the source code
git clone https://github.com/yourname/mediaclean.git
cd mediaclean

# 2. (Optional) Create a virtual environment
python -m venv .venv
.venv\Scripts\activate      # For Windows

# 3. Install required packages
pip install -r requirements.txt

# 4. Run the application
python main.py
```

### Dependencies (`requirements.txt`)
- `PyQt6`: Graphical User Interface (GUI).
- `send2trash`: Ensures files are safely moved to the Recycle Bin instead of being permanently deleted.
- `Pillow` & `rawpy` (with `numpy`): Supports reading and displaying thumbnails for both standard and RAW images.
