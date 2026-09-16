import re
from html import unescape


_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"[ \t]+")
_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")
_ID_PATTERN = re.compile(r"(?<!\d)(700\d{7})(?!\d)")


def clean_body(body: str) -> str:
    """Convert HTML/plain text into compact readable text."""
    text = unescape(body or "")
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_PATTERN.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_WHITESPACE_PATTERN.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    return _BLANK_LINES_PATTERN.sub("\n\n", text).strip()


def find_email_id(text: str) -> str:
    """Return the first 10-digit identifier beginning with 700."""
    match = _ID_PATTERN.search(text or "")
    return match.group(1) if match else ""