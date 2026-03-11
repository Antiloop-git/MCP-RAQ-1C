"""Парсеры справки платформы 1С (HBK) и БСП (HTML)."""

import io
import re
import struct
import zipfile
from html.parser import HTMLParser
from pathlib import Path


class _HTMLTextExtractor(HTMLParser):
    """Simple HTML→text extractor."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "li", "tr"):
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self._parts)).strip()


def _html_to_text(html: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _chunk_text(text: str, max_tokens: int = 500, overlap: int = 100) -> list[str]:
    """Split text into chunks by approximate token count (1 token ≈ 4 chars for Russian)."""
    chars_per_token = 4
    max_chars = max_tokens * chars_per_token
    overlap_chars = overlap * chars_per_token

    if len(text) <= max_chars:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        # Try to break at paragraph/sentence boundary
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", ", ", " "]:
                pos = text.rfind(sep, start + max_chars // 2, end)
                if pos > start:
                    end = pos + len(sep)
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap_chars
    return [c for c in chunks if c]


def _read_v8_block_chain(data: bytes, offset: int) -> bytes:
    """Read a block chain from 1C v8 container format.

    Each block has a 31-byte ASCII header: \\r\\n{total_hex} {page_hex} {next_hex} \\r\\n
    """
    result = bytearray()
    total_size = None
    while offset != 0x7FFFFFFF and offset < len(data):
        header = data[offset:offset + 31]
        if len(header) < 31 or header[:2] != b"\r\n":
            break
        text = header[2:29].strip()
        parts = text.split()
        if len(parts) < 3:
            break
        if total_size is None:
            total_size = int(parts[0], 16)
        page_size = int(parts[1], 16)
        next_block = int(parts[2], 16)
        remaining = total_size - len(result)
        to_read = min(page_size, remaining)
        result.extend(data[offset + 31:offset + 31 + to_read])
        if next_block == 0x7FFFFFFF or len(result) >= total_size:
            break
        offset = next_block
    return bytes(result)


def _extract_hbk_html_files(hbk_path: Path) -> zipfile.ZipFile:
    """Extract FileStorage ZIP from 1C HBK container.

    HBK uses 1C v8 container format with entities: Book, FileStorage, PackBlock, etc.
    FileStorage contains a ZIP archive with HTML documentation pages.
    """
    data = hbk_path.read_bytes()

    # Parse TOC: starts at offset 0x2f (after 16-byte header + 31-byte TOC block header)
    toc_start = 0x2F
    # TOC first block header at offset 0x10 tells us total data size
    toc_header = data[0x10:0x10 + 31]
    toc_text = toc_header[2:29].strip()
    toc_parts = toc_text.split()
    toc_data_size = int(toc_parts[0], 16)

    toc_data = data[toc_start:toc_start + toc_data_size]

    # TOC is array of 12-byte entries: (header_addr, body_addr, end_marker)
    file_storage_body = None
    for i in range(0, len(toc_data) - 8, 12):
        hdr_addr, body_addr, _ = struct.unpack_from("<III", toc_data, i)
        if hdr_addr == 0 and body_addr == 0:
            break
        # Read entity name from header block
        name_data = _read_v8_block_chain(data, hdr_addr)
        try:
            name = name_data.decode("utf-16-le").rstrip("\x00").strip()
        except Exception:
            continue
        if name.endswith("FileStorage"):
            file_storage_body = body_addr
            break

    if file_storage_body is None:
        raise ValueError("FileStorage entity not found in HBK container")

    fs_data = _read_v8_block_chain(data, file_storage_body)
    return zipfile.ZipFile(io.BytesIO(fs_data))


def parse_hbk(hbk_path: Path) -> list[dict]:
    """Parse 1C HBK help file (v8 container with HTML inside FileStorage ZIP).

    Returns list of {title, section, content} chunks.
    """
    if not hbk_path.exists():
        raise FileNotFoundError(f"HBK file not found: {hbk_path}")

    chunks = []
    zf = _extract_hbk_html_files(hbk_path)

    for name in zf.namelist():
        try:
            raw = zf.read(name)
            # Try common encodings
            for enc in ("utf-8", "windows-1251", "cp1251"):
                try:
                    html = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                html = raw.decode("utf-8", errors="replace")

            # Skip non-HTML content
            if "<html" not in html.lower() and "<body" not in html.lower():
                continue

            title = _extract_title(html) or name
            # Extract first H1 as title if no <title>
            if not title or title == name:
                m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
                if m:
                    title = re.sub(r"<[^>]+>", "", m.group(1)).strip()

            text = _html_to_text(html)

            if len(text) < 20:
                continue

            for chunk in _chunk_text(text):
                chunks.append({
                    "title": title or name,
                    "section": name,
                    "content": chunk,
                })
        except Exception:
            continue

    zf.close()
    return chunks


def parse_bsp_help(config_path: Path) -> list[dict]:
    """Parse BSP help HTML files from configuration export.

    Scans config_path/**/Help/ru.html recursively.
    Returns list of {subsystem, title, content, source_path} chunks.
    """
    chunks = []
    help_files = sorted(config_path.rglob("*/Help/ru.html"))

    for html_path in help_files:
        try:
            html = html_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                html = html_path.read_text(encoding="windows-1251")
            except Exception:
                continue

        # Extract subsystem name from path:
        # .../Subsystems/Name/Ext/Help/ru.html → Name
        # .../Subsystems/Parent/Subsystems/Child/Ext/Help/ru.html → Child
        parts = html_path.parts
        subsystem = ""
        for i in range(len(parts) - 1, -1, -1):
            if parts[i] == "Ext" and i >= 2:
                subsystem = parts[i - 1]
                break

        title = _extract_title(html) or subsystem
        text = _html_to_text(html)

        if len(text) < 20:
            continue

        rel_path = str(html_path.relative_to(config_path)) if config_path in html_path.parents else str(html_path)

        for chunk in _chunk_text(text):
            chunks.append({
                "subsystem": subsystem,
                "title": title,
                "content": chunk,
                "source_path": rel_path,
            })

    return chunks
