import re
from dataclasses import dataclass
from datetime import datetime


def internalDate_to_str(internal_date:str) -> datetime:
    assert(isinstance(internal_date, str))
    return datetime.fromtimestamp(int(internal_date) / 1000)


# Regex that matches "On <date>, <name> <email> wrote:" and captures (date_str, sender_name, sender_email)
# Uses greedy (.+) for date to consume everything up to the last ", Name <email>" portion
QUOTE_HEADER_RE = re.compile(
    r'^On\s+(.+),\s+([^<]+?)\s+<([^>]+)>\s*wrote:\s*$',
    re.MULTILINE
)

# Patterns used to detect the start of quoted/forwarded content (no capturing needed)
QUOTE_START_PATTERNS = [
    # Outlook with mailto
    r'^On [^\n]+<[^>]+<mailto:[^>]+>>\s*wrote:',

    # Gmail with "at" separator: On Mon, 12 Jan 2026 at 10:58, Name <email> wrote:
    r'^On \w{3}, \d{1,2} \w{3} \d{4} at \d{1,2}:\d{2}[^\n]+<[^>]+>\s*wrote:',

    # Gmail with comma separator: On Mon, 12 Jan 2026, 10:58, Name <email> wrote:
    r'^On \w{3}, \d{1,2} \w{3} \d{4}, \d{1,2}:\d{2}[^\n]+<[^>]+>\s*wrote:',

    # Date with slashes: On 12/01/2026, Name <email> wrote:
    r'^On \d{1,2}/\d{1,2}/\d{4}[^\n]+<[^>]+>\s*wrote:',

    # Long day name format: On Thursday, 12 Jan 2026, 10:58, Name <email> wrote:
    r'^On .+?, \d{1,2} \w{3} \d{4},? \d{1,2}:\d{2}[^\n]+<[^>]+>\s*wrote:',

    # Zendesk/ticket system format with UTC timestamp
    r'^On \d{1,2} \w+ \d{4} at \d{2}:\d{2}:\d{2} UTC,[^\n]+wrote:',

    # Email header block (only when multiple headers appear together)
    r'^From:\s+[^\n]+@[^\n]+\nTo:\s+[^\n]+\nSubject:\s+',
    r'^Sent:\s+[^\n]+\nFrom:\s+[^\n]+@[^\n]+',

    # Forwarded/original message separators
    r'^-{3,}\s*Original Message\s*-{3,}',
    r'^-{3,}\s*Forwarded message\s*-{3,}',
    r'^---------- Forwarded message',
]


def remove_gmail_trailing_quoted_content(text:str) -> str:
    """Remove Gmail quoted content from email text"""
    assert(isinstance(text, str))

    # Find the earliest match
    position_to_slice = len(text)

    for pattern in QUOTE_START_PATTERNS:
        # MULTILINE: ^ matches line starts
        # IGNORECASE: case-insensitive matching
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match and match.start() < position_to_slice:
            position_to_slice = match.start()

    if position_to_slice < len(text):
        text = text[:position_to_slice].rstrip()

    return text


@dataclass
class QuotedBlock:
    sender_email: str
    sender_name: str
    date_str: str
    content: str


def extract_quoted_blocks(text: str) -> list[QuotedBlock]:
    """Extract quoted email blocks from email text.

    Parses "On <date>, <name> <email> wrote:" headers followed by > prefixed lines.
    Handles nested quotes by recursively parsing stripped content.
    Returns a flat list of QuotedBlock objects (outermost/newest first).
    """
    blocks: list[QuotedBlock] = []

    for match in QUOTE_HEADER_RE.finditer(text):
        date_str = match.group(1).strip()
        sender_name = match.group(2).strip()
        sender_email = match.group(3).strip()

        # Collect > prefixed lines after the header
        after_header = text[match.end():]
        quoted_lines: list[str] = []
        for line in after_header.split('\n'):
            stripped = line.strip()
            if stripped.startswith('>') or stripped == '':
                quoted_lines.append(line)
            elif len(quoted_lines) > 0:
                # Stop at first non-empty, non-quoted line
                break

        # Strip one level of > prefix
        content_lines: list[str] = []
        for line in quoted_lines:
            stripped = line.strip()
            if stripped.startswith('>'):
                # Remove first > and optional space after it
                after_gt = stripped[1:]
                if after_gt.startswith(' '):
                    after_gt = after_gt[1:]
                content_lines.append(after_gt)
            else:
                content_lines.append(stripped)

        content = '\n'.join(content_lines).strip()

        if content:
            blocks.append(QuotedBlock(
                sender_email=sender_email,
                sender_name=sender_name,
                date_str=date_str,
                content=content
            ))

            # Recursively extract nested quotes from the stripped content
            nested = extract_quoted_blocks(content)
            blocks.extend(nested)

    return blocks


def remove_cid_references(text:str):
    """Remove all [cid:...] references from text"""
    
    # Pattern matches [cid: followed by any characters until ]
    pattern = r'\[cid:[^\]]+\]'
    
    # Remove them completely
    cleaned = re.sub(pattern, '', text)
    
    return cleaned