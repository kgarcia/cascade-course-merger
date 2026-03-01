# Cascade Course Merger

Merge [Cascade LMS](https://www.hannonhill.com/products/cascade-cms-web-content-management/index.html) course export `.zip` files into a single combined HTML per module — with all images and assets extracted so everything renders correctly in a browser.

Cross-platform GUI (tkinter) and CLI. No dependencies beyond Python 3.
<img width="717" height="525" alt="image" src="https://github.com/user-attachments/assets/e29aa825-3b30-4c9c-bd2a-6f4019db71b2" />

## Quick Start

### GUI

| Platform | Launch |
|----------|--------|
| **Windows** | Double-click `run.bat` |
| **macOS** | Double-click `run.command` |

Or run directly:

```bash
python3 cascade_merge_gui.py
```

1. Click **+ Add Zip Files** and select one or more Cascade `.zip` exports.
2. Click **Merge All**.
3. Each zip produces an output folder containing:
   - `module_XX_combined.html` — open this in a browser
   - `course_files/` — images and assets (keep alongside the HTML)
   - `Table of Contents.html`
4. Click **Preview in Browser** or **Open Folder** to see results.

### CLI

```bash
python3 cascade_merge.py export.zip
python3 cascade_merge.py file1.zip file2.zip file3.zip
python3 cascade_merge.py export.zip -o /path/to/output_dir
```

## Requirements

- **Python 3.8+** with tkinter (included by default on Windows and most macOS installs)
- No `pip install` needed — everything is Python standard library

### Installing tkinter (if needed)

| Platform | Command |
|----------|---------|
| macOS (Homebrew) | `brew install python-tk` |
| Ubuntu / Debian | `sudo apt install python3-tk` |
| Windows | Included with the [python.org](https://www.python.org/downloads/) installer (check "tcl/tk" during install) |

## Expected Zip Structure

The input `.zip` should be a Cascade CMS course export containing:

```
course_files/
  module_XX/
    01_firstPage.html
    02_secondPage.html
    ...
    img/
    doc/
  CodeBox/          (optional)
Table of Contents.html
```

## How It Works

1. Reads all numbered HTML section files from the zip
2. Extracts the body content from each, stripping scripts and duplicate footers
3. Concatenates them with section separators and page-break hints
4. Detects and includes extra assets (Quiz CSS/JS, CodeBox syntax highlighting)
5. Rewrites relative `img/` and `doc/` paths so they resolve from the output location
6. Extracts all supporting assets (images, docs, CodeBox) alongside the combined HTML
7. Writes a single self-contained `module_XX_combined.html`

## License

[MIT](LICENSE)
