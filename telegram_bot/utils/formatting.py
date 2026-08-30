"""
Message formatting helpers for Telegram bot.

Telegram messages have no native table entity, so tables are rendered as
fixed-width monospace text wrapped in an HTML <pre> block.
"""
import html
from typing import Any, List, Sequence

from telegram.constants import MessageLimit

COLUMN_GAP = "  "


def _build_table_text(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    str_headers = [str(h) for h in headers]
    str_rows = [[str(cell) for cell in row] for row in rows]

    widths = [len(h) for h in str_headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def render_line(cells: List[str]) -> str:
        padded = [html.escape(cell.ljust(widths[i])) for i, cell in enumerate(cells)]
        return COLUMN_GAP.join(padded).rstrip()

    lines = [render_line(str_headers)]
    lines.append("-" * (sum(widths) + len(COLUMN_GAP) * (len(widths) - 1)))
    lines.extend(render_line(row) for row in str_rows)

    return "\n".join(lines)


def render_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """
    Render headers/rows as a monospace HTML table for parse_mode=HTML.

    Cell values are stringified and HTML-escaped; column widths are computed
    from the unescaped text so alignment matches what Telegram renders. Rows
    are dropped from the end (with a note) if the table would exceed
    Telegram's message length limit.
    """
    visible_rows = list(rows)
    while True:
        wrapped = f"<pre>{_build_table_text(headers, visible_rows)}</pre>"
        if len(wrapped) <= MessageLimit.MAX_TEXT_LENGTH or not visible_rows:
            break
        visible_rows = visible_rows[:-1]

    dropped = len(rows) - len(visible_rows)
    if dropped:
        wrapped += f"\n<i>...{dropped} more row(s) not shown (message too long)</i>"

    return wrapped
