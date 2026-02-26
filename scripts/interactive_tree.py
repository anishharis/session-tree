#!/usr/bin/env python3
"""
Interactive session tree browser.
Navigate with arrow keys, Enter to resume a session, q to quit.
"""

import curses
import os
import subprocess
import sys

# Add parent dir so we can import build_tree
sys.path.insert(0, os.path.dirname(__file__))
from build_tree import build_tree_json, format_timestamp


def flatten_tree(tree_data):
    """Flatten the tree into a list of (indent, session_info, session_id, has_children) tuples."""
    session_map = tree_data["sessions"]
    children = tree_data["children"]
    roots = tree_data["roots"]
    rows = []

    def walk(sid, depth=0):
        s = session_map.get(sid, {})
        name = s.get("name") or s.get("firstPrompt", "")[:60] or "(no prompt)"
        ts = format_timestamp(s.get("firstTimestamp", ""))
        msgs = s.get("messageCount", 0)
        child_ids = children.get(sid, [])
        child_ids.sort(key=lambda c: session_map.get(c, {}).get("firstTimestamp", ""))
        rows.append((depth, ts, msgs, name, sid, len(child_ids) > 0))
        for child in child_ids:
            walk(child, depth + 1)

    for root in roots:
        walk(root)

    return rows


def draw_tree(stdscr, rows, selected, scroll_offset, filter_text=""):
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    # Header
    header = " SESSION TREE  (↑↓ navigate | Enter resume | / search | q quit)"
    stdscr.attron(curses.color_pair(3))
    stdscr.addnstr(0, 0, header.ljust(width), width - 1)
    stdscr.attroff(curses.color_pair(3))

    # Filter bar
    if filter_text is not None:
        filter_line = f" Filter: {filter_text}█"
        stdscr.attron(curses.color_pair(4))
        stdscr.addnstr(1, 0, filter_line.ljust(width), width - 1)
        stdscr.attroff(curses.color_pair(4))
        content_start = 2
    else:
        content_start = 1

    # Tree rows
    visible_rows = height - content_start - 2  # leave room for footer
    for i in range(visible_rows):
        row_idx = i + scroll_offset
        if row_idx >= len(rows):
            break

        depth, ts, msgs, name, sid, has_children = rows[row_idx]

        # Build tree prefix
        indent = "  " * depth
        if has_children:
            marker = "▸ "
        else:
            marker = "  "

        # Truncate name to fit
        meta = f"{indent}{marker}{ts} ({msgs}) "
        max_name = max(10, width - len(meta) - 2)
        display_name = name[:max_name - 1] + "…" if len(name) > max_name else name
        line = f"{indent}{marker}{ts} ({msgs}) {display_name}"

        y = i + content_start
        if row_idx == selected:
            stdscr.attron(curses.color_pair(1))
            stdscr.addnstr(y, 0, line.ljust(width - 1), width - 1)
            stdscr.attroff(curses.color_pair(1))
        elif has_children:
            stdscr.attron(curses.color_pair(2))
            stdscr.addnstr(y, 0, line, width - 1)
            stdscr.attroff(curses.color_pair(2))
        else:
            stdscr.addnstr(y, 0, line, width - 1)

    # Footer with selected session info
    if rows:
        _, _, _, _, sid, _ = rows[selected]
        footer = f" {sid}"
        stdscr.attron(curses.color_pair(3))
        stdscr.addnstr(height - 1, 0, footer.ljust(width), width - 1)
        stdscr.attroff(curses.color_pair(3))

    stdscr.refresh()


def main(stdscr, project_path):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)    # selected
    curses.init_pair(2, curses.COLOR_CYAN, -1)                     # has children
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)    # header/footer
    curses.init_pair(4, curses.COLOR_YELLOW, -1)                   # filter bar

    tree = build_tree_json(project_path)
    all_rows = flatten_tree(tree)

    if not all_rows:
        stdscr.addstr(0, 0, "No sessions found.")
        stdscr.getch()
        return None

    rows = all_rows
    selected = 0
    scroll_offset = 0
    filter_text = None
    selected_sid = None

    while True:
        height, width = stdscr.getmaxyx()
        content_start = 2 if filter_text is not None else 1
        visible = height - content_start - 2

        # Keep selected in view
        if selected < scroll_offset:
            scroll_offset = selected
        if selected >= scroll_offset + visible:
            scroll_offset = selected - visible + 1

        draw_tree(stdscr, rows, selected, scroll_offset, filter_text)

        key = stdscr.getch()

        if filter_text is not None:
            # In search mode
            if key == 27:  # Escape - cancel search
                filter_text = None
                rows = all_rows
                selected = 0
                scroll_offset = 0
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                filter_text = filter_text[:-1]
                if not filter_text:
                    rows = all_rows
                else:
                    rows = [r for r in all_rows if filter_text.lower() in r[3].lower()]
                selected = min(selected, max(0, len(rows) - 1))
                scroll_offset = 0
            elif key == 10:  # Enter - accept search and go back to nav
                filter_text = None
            elif 32 <= key <= 126:
                filter_text += chr(key)
                rows = [r for r in all_rows if filter_text.lower() in r[3].lower()]
                selected = min(selected, max(0, len(rows) - 1))
                scroll_offset = 0
            continue

        # Normal navigation mode
        if key == ord("q") or key == 27:
            return None
        elif key == curses.KEY_UP or key == ord("k"):
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            selected = min(len(rows) - 1, selected + 1)
        elif key == curses.KEY_PPAGE:  # Page Up
            selected = max(0, selected - visible)
        elif key == curses.KEY_NPAGE:  # Page Down
            selected = min(len(rows) - 1, selected + visible)
        elif key == ord("g"):  # Go to top
            selected = 0
            scroll_offset = 0
        elif key == ord("G"):  # Go to bottom
            selected = len(rows) - 1
        elif key == ord("/"):  # Search
            filter_text = ""
        elif key == 10:  # Enter - resume
            if rows:
                _, _, _, _, sid, _ = rows[selected]
                selected_sid = sid
                return selected_sid


def run(project_path=None):
    result = curses.wrapper(main, project_path)
    if result:
        print(f"Resuming session: {result}")
        print(f"Run: claude --resume {result}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    run(path)
