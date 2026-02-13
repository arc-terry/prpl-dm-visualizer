"""Shared helpers for TR-181 visualizer scripts."""

import re
import shutil
import sys
import unicodedata

RECOMMENDED_WIDTH = 80


def get_term_width():
    """Return terminal width, defaulting to 80."""
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def warn_narrow_width(width=None, recommended=RECOMMENDED_WIDTH):
    """Print a warning if terminal width is below the recommended value."""
    if width is None:
        width = get_term_width()
    if width < recommended:
        print(f'⚠ Warning: terminal width is {width} cols; '
              f'recommended >= {recommended} cols.',
              file=sys.stderr)
    return width


def parse_dm(filepath):
    """Parse DM.txt into a dict of {path: value}."""
    dm = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            m = re.match(r'^(Device\..+?)=(.*)$', line)
            if m:
                dm[m.group(1)] = m.group(2).strip('"')
    return dm


def get_attr(dm, prefix, attr):
    """Get attribute, trying with/without double dot."""
    for key in [f"{prefix}.{attr}", f"{prefix}..{attr}"]:
        if key in dm:
            return dm[key]
    return None


def display_width(text):
    """Return the display width of text, accounting for wide/emoji chars."""
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width


def pad_display(text, width, fill=' '):
    """Pad text to a target display width."""
    pad = width - display_width(text)
    if pad <= 0:
        return text
    return text + (fill * pad)


def fit_display(text, width, fill=' '):
    """Truncate and pad text to exactly the given display width."""
    if display_width(text) <= width:
        return pad_display(text, width, fill)
    clipped = []
    used = 0
    for ch in text:
        if unicodedata.combining(ch):
            clipped.append(ch)
            continue
        w = 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1
        if used + w > width:
            break
        clipped.append(ch)
        used += w
    return pad_display(''.join(clipped), width, fill)


def hline(char, width, left='', right=''):
    """Draw a horizontal line fitting the given width."""
    inner = width - len(left) - len(right)
    return f'{left}{char * inner}{right}'


def boxline(text, width, pad=2, fill=' '):
    """Render a left-aligned text line inside a box of given width."""
    inner = width - 2
    content = f'{" " * pad}{text}'
    if display_width(content) > inner:
        return f'│{content}│'
    return f'│{pad_display(content, inner, fill)}│'


def box_width(min_width, lines, pad=2, title=None):
    """Compute the box width needed to fit all lines."""
    inner = max(min_width - 2, 0)
    max_line = 0
    if title:
        max_line = max(max_line, display_width(title))
    for line in lines:
        max_line = max(max_line, display_width(line) + pad)
    if max_line > inner:
        inner = max_line
    return inner + 2
