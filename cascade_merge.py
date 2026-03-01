#!/usr/bin/env python3
"""
Cascade Course → Combined HTML
===============================
Merges all HTML sections from a Cascade LMS course export into a single
combined HTML file.

Usage:
    python3 cascade_merge.py course_export.zip
    python3 cascade_merge.py course_export.zip -o output.html
    python3 cascade_merge.py course_export.zip course2.zip course3.zip

The input is a .zip exported from Cascade containing:
    course_files/module_XX/*.html   (numbered section pages)
    course_files/module_XX/img/     (images)
    course_files/CodeBox/           (optional syntax highlighting assets)
    Table of Contents.html

The output is a single <module_name>_combined.html written next to the zip
(or to -o path if specified).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
from pathlib import Path


# ---------------------------------------------------------------------------
# HTML extraction helpers
# ---------------------------------------------------------------------------

def extract_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else "Module"


def extract_body_content(html: str) -> str:
    """Return the row content inside splash-container, stripping footer and scripts."""
    body_match = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL | re.IGNORECASE)
    if not body_match:
        return ""
    body = body_match.group(1)
    body = re.sub(r"<script\b[^>]*>.*?</script>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<noscript\b[^>]*>.*?</noscript>", "", body, flags=re.DOTALL | re.IGNORECASE)
    splash = re.search(
        r'<div class="splash-container">\s*<div class="container-fluid">\s*<div class="row">(.*)</div>\s*</div>\s*</div>',
        body,
        re.DOTALL,
    )
    if not splash:
        return body.strip()
    row_content = splash.group(1)
    row_content = re.sub(
        r'<div class="col-12">\s*<footer>.*?</footer>\s*</div>',
        "",
        row_content,
        flags=re.DOTALL,
    )
    return row_content.strip()


def extract_footer(html: str) -> str:
    body_match = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL | re.IGNORECASE)
    if not body_match:
        return ""
    body = body_match.group(1)
    footer_match = re.search(
        r'<div class="col-12">\s*<footer>(.*?)</footer>\s*</div>',
        body,
        re.DOTALL,
    )
    if not footer_match:
        return ""
    return (
        '<div class="col-12">\n\t\t\t\t\t<footer>\n'
        + footer_match.group(1).strip()
        + "\n\t\t\t\t\t</footer>\n\t\t\t\t</div>"
    )


# ---------------------------------------------------------------------------
# Zip introspection
# ---------------------------------------------------------------------------

def discover_module(zf: zipfile.ZipFile) -> tuple[str, str, list[str]]:
    """
    Find the module_XX directory and its numbered HTML files inside the zip.
    Returns (module_name, module_prefix, sorted_html_names).
    """
    html_files: dict[str, list[str]] = {}
    for entry in zf.namelist():
        parts = entry.split("/")
        if (
            len(parts) >= 3
            and parts[0] == "course_files"
            and parts[1].startswith("module_")
            and parts[-1].endswith(".html")
            and parts[-1][0].isdigit()
        ):
            module_name = parts[1]
            html_files.setdefault(module_name, []).append(entry)

    if not html_files:
        raise ValueError("No course_files/module_XX/*.html files found in zip.")

    module_name = sorted(html_files.keys())[0]
    entries = sorted(html_files[module_name], key=lambda p: os.path.basename(p))
    prefix = f"course_files/{module_name}"

    return module_name, prefix, entries


def scan_assets(zf: zipfile.ZipFile, html_entries: list[str]) -> tuple[bool, bool, bool]:
    has_quiz_css = False
    has_quiz_js = False
    has_codebox = False
    for entry in html_entries:
        content = zf.read(entry).decode("utf-8", errors="replace")
        if "quiz.min.css" in content:
            has_quiz_css = True
        if "quiz.min.js" in content:
            has_quiz_js = True
        if "codeBox.css" in content or "codeBox.js" in content:
            has_codebox = True
    return has_quiz_css, has_quiz_js, has_codebox


def peek_module_name(zip_path: str) -> str:
    """Quick check: return the module_XX name from a zip without extracting."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        module_name, _, _ = discover_module(zf)
    return module_name


# ---------------------------------------------------------------------------
# Core merge
# ---------------------------------------------------------------------------

def extract_assets(zf: zipfile.ZipFile, out_dir: str, module_html_entries: set[str]):
    """Extract all supporting assets (images, CodeBox, docs, videos) from the
    zip into out_dir, skipping the individual module HTML pages (they're merged)."""
    for entry in zf.namelist():
        if entry.endswith("/"):
            continue
        if entry in module_html_entries:
            continue
        dest = os.path.join(out_dir, entry)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with zf.open(entry) as src, open(dest, "wb") as dst:
            dst.write(src.read())


def merge_from_zip(zip_path: str, output_dir: str | None = None,
                   progress_callback=None) -> str:
    """Read a Cascade zip, extract assets, and produce a combined HTML file.
    Returns the path to the combined HTML.
    progress_callback, if provided, is called with (message: str) for status updates."""
    def _log(msg):
        if progress_callback:
            progress_callback(msg)
        print(msg)

    zip_abs = os.path.abspath(zip_path)

    if not output_dir:
        zip_name = os.path.splitext(os.path.basename(zip_abs))[0]
        output_dir = os.path.join(os.path.dirname(zip_abs), zip_name)

    os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        module_name, prefix, html_entries = discover_module(zf)
        has_quiz_css, has_quiz_js, has_codebox = scan_assets(zf, html_entries)

        _log(f"  Module: {module_name} ({len(html_entries)} sections)")
        _log(f"  Extracting assets to: {output_dir}/")
        extract_assets(zf, output_dir, set(html_entries))

        first_html = zf.read(html_entries[0]).decode("utf-8", errors="replace")
        last_html = zf.read(html_entries[-1]).decode("utf-8", errors="replace")
        title = extract_title(first_html)

        img_prefix = f"course_files/{module_name}/img"
        doc_prefix = f"course_files/{module_name}/doc"
        codebox_prefix = "course_files/CodeBox"

        sections = []
        for i, entry in enumerate(html_entries):
            html = zf.read(entry).decode("utf-8", errors="replace")
            content = extract_body_content(html)
            if not content:
                continue
            content = content.replace('src="img/', f'src="{img_prefix}/')
            content = content.replace("src='img/", f"src='{img_prefix}/")
            content = content.replace('href="doc/', f'href="{doc_prefix}/')
            content = content.replace("href='doc/", f"href='{doc_prefix}/")
            if i > 0:
                content = (
                    '\n\t\t\t\t<div class="section-sep" style="page-break-before: always;"></div>\n\t\t\t\t'
                    + content
                )
            sections.append(content)

    footer = extract_footer(last_html)
    body_inner = "\n\t\t\t\t".join(sections) + "\n\t\t\t\t" + footer

    extra_css = ""
    if has_quiz_css:
        extra_css += '\t\t<link rel="stylesheet" href="/shared/LCS_IATs/Quiz/css/quiz.min.css" />\n'
    if has_codebox:
        extra_css += f'\t\t<link rel="stylesheet" href="{codebox_prefix}/codeBox.css" />\n'
        extra_css += f'\t\t<link rel="stylesheet" href="{codebox_prefix}/railscasts.min.css" />\n'

    extra_js = ""
    if has_quiz_js:
        extra_js += '\t\t<script src="/shared/LCS_IATs/Quiz/js/quiz.min.js"></script>\n'
    if has_codebox:
        extra_js += f'\t\t<script src="{codebox_prefix}/highlight.js"></script>\n'
        extra_js += f'\t\t<script src="{codebox_prefix}/codeBox.js"></script>\n'

    combined = f"""<!DOCTYPE html>
<html lang="en">
\t<head>
\t\t<meta charset="utf-8" />
\t\t<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
\t\t<link rel="stylesheet" href="/shared/LCS_HTML_Templates/UNF_Template_2023/_assets/thirdpartylib/bootstrap-4.6.1/css/bootstrap.min.css" />
\t\t<link rel="stylesheet" href="/shared/LCS_HTML_Templates/UNF_Template_2023/_assets/thirdpartylib/fontawesome-free-5.9.0-web/css/all.min.css" />
\t\t<link rel="stylesheet" href="/shared/LCS_HTML_Templates/UNF_Template_2023/_assets/css/theme.min.css" />
\t\t<link rel="stylesheet" href="/shared/LCS_HTML_Templates/UNF_Template_2023/_assets/css/custom.min.css" />
{extra_css}\t\t<title>{title} (Full Module)</title>
\t\t<style>
\t\t\t@media print {{
\t\t\t\t.collapse {{ display: block !important; }}
\t\t\t\t.collapse:not(.show) {{ display: block !important; }}
\t\t\t\t.flip-card-back {{ opacity: 1 !important; position: relative !important; }}
\t\t\t\t.flip-card-front {{ opacity: 0 !important; position: absolute !important; }}
\t\t\t\t.tab-pane {{ display: block !important; }}
\t\t\t\t.section-sep {{ page-break-before: always; margin-top: 2rem; border-top: 1px solid #dee2e6; padding-top: 2rem; }}
\t\t\t}}
\t\t\t.section-sep {{ margin-top: 2rem; border-top: 1px solid #dee2e6; padding-top: 2rem; }}
\t\t</style>
\t</head>
\t<body class="template-fallback">
\t\t<div class="splash-container">
\t\t\t<div class="container-fluid">
\t\t\t\t<div class="row">
{body_inner}
\t\t\t\t</div>
\t\t\t</div>
\t\t</div>
\t\t<script src="/shared/LCS_HTML_Templates/UNF_Template_2023/_assets/thirdpartylib/jquery/jquery-3.5.1.min.js"></script>
\t\t<script src="/shared/LCS_HTML_Templates/UNF_Template_2023/_assets/thirdpartylib/popper-js/popper.min.js"></script>
\t\t<script src="/shared/LCS_HTML_Templates/UNF_Template_2023/_assets/thirdpartylib/bootstrap-4.6.1/js/bootstrap.min.js"></script>
\t\t<script src="/shared/LCS_HTML_Templates/UNF_Template_2023/_assets/js/scripts.min.js"></script>
{extra_js}\t</body>
</html>
"""

    html_path = os.path.join(output_dir, f"{module_name}_combined.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(combined)

    return html_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Merge a Cascade LMS course export zip into a single combined HTML.",
        epilog="Example: python3 cascade_merge.py export.zip",
    )
    parser.add_argument(
        "zips",
        nargs="+",
        metavar="FILE.zip",
        help="One or more Cascade course export zip files.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        metavar="DIR",
        default=None,
        help="Output directory (only valid with a single zip). "
             "Defaults to a folder named after the zip.",
    )
    args = parser.parse_args()

    if args.output_dir and len(args.zips) > 1:
        parser.error("-o/--output-dir can only be used with a single zip file.")

    for zip_path in args.zips:
        if not os.path.isfile(zip_path):
            print(f"SKIP (not found): {zip_path}", file=sys.stderr)
            continue
        if not zipfile.is_zipfile(zip_path):
            print(f"SKIP (not a zip): {zip_path}", file=sys.stderr)
            continue

        print(f"Processing: {os.path.basename(zip_path)}")
        html_path = merge_from_zip(zip_path, args.output_dir)
        print(f"  -> {html_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
