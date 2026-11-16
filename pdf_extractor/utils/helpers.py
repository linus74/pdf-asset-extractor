"""
Common utility functions: date parsing, string sanitization, hashing, formatting.
"""

import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional


def parse_pdf_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parses a PDF date string (e.g., "D:20240315143000+01'00'") into ISO 8601 string.
    """
    if not date_str or not isinstance(date_str, str):
        return None

    clean = date_str.strip()
    if clean.startswith("D:"):
        clean = clean[2:]

    # Remove apostrophes in timezone, e.g. +01'00' -> +01:00
    # Standard format: YYYYMMDDHHmmSS[+-]HH'mm'
    pattern = r"^(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([+\-Zz])?(\d{2})?'?(\d{2})?'?"
    match = re.match(pattern, clean)
    if not match:
        return date_str

    groups = match.groups()
    year = int(groups[0])
    month = int(groups[1]) if groups[1] else 1
    day = int(groups[2]) if groups[2] else 1
    hour = int(groups[3]) if groups[3] else 0
    minute = int(groups[4]) if groups[4] else 0
    second = int(groups[5]) if groups[5] else 0
    tz_sign = groups[6]
    tz_hour = int(groups[7]) if groups[7] else 0
    tz_min = int(groups[8]) if groups[8] else 0

    tz = timezone.utc
    if tz_sign in ("+", "-"):
        offset = timedelta(hours=tz_hour, minutes=tz_min)
        if tz_sign == "-":
            offset = -offset
        tz = timezone(offset)

    try:
        dt = datetime(year, month, day, hour, minute, second, tzinfo=tz)
        return dt.isoformat()
    except Exception:
        return date_str


def sanitize_filename(name: str, max_length: int = 120, fallback: str = "asset") -> str:
    """
    Cleans a string so it can be safely used as a filename across Windows, macOS, and Linux.
    """
    if not name or not isinstance(name, str):
        return fallback

    # Replace invalid chars: \ / : * ? " < > | + # % & { } $ ! ' @ ` =
    sanitized = re.sub(r'[\\/*?:"<>|+%!\'`=,;]', "_", name)
    sanitized = re.sub(r"\s+", "_", sanitized)
    sanitized = sanitized.strip("._ ")

    if not sanitized:
        sanitized = fallback

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("._ ")

    return sanitized


def format_bytes(size: int) -> str:
    """
    Formats byte count into human readable string (B, KB, MB, GB).
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


def compute_sha256(data: bytes) -> str:
    """Computes SHA-256 hex digest of data."""
    return hashlib.sha256(data).hexdigest()
