"""Парсеры справки платформы 1С (HBK) и БСП (HTML)."""

import re
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


def parse_hbk(hbk_path: Path) -> list[dict]:
    """Parse 1C HBK help file (zip archive with HTML).

    Returns list of {title, section, content} chunks.
    """
    if not hbk_path.exists():
        raise FileNotFoundError(f"HBK file not found: {hbk_path}")

    chunks = []
    with zipfile.ZipFile(hbk_path, "r") as zf:
        html_files = [n for n in zf.namelist() if n.lower().endswith((".html", ".htm"))]
        for name in html_files:
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

                title = _extract_title(html) or Path(name).stem
                section = str(Path(name).parent)
                text = _html_to_text(html)

                if len(text) < 20:
                    continue

                for chunk in _chunk_text(text):
                    chunks.append({
                        "title": title,
                        "section": section,
                        "content": chunk,
                    })
            except Exception:
                continue

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
