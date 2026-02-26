#!/usr/bin/env python3
"""
Interactive session tree browser.
Navigate with arrow keys, Enter to resume a session, q to quit.
Left/right arrows collapse/expand nodes with children.
"""

import curses
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_tree import build_tree_json, format_timestamp


def build_full_rows(tree_data):
    """Build full flat list of all rows with parent info."""
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
        rows.append((depth, ts, msgs, name, sid, child_ids))
        for child in child_ids:
            walk(child, depth + 1)

    for root in roots:
        walk(root)

    return rows


def get_visible_rows(all_rows, collapsed):
    """Filter rows based on collapsed set. Skip children of collapsed nodes."""
    visible = []
    skip_depth = None

    for depth, ts, msgs, name, sid, child_ids in all_rows:
        if skip_depth is not None and depth > skip_depth:
            continue
        skip_depth = None

        has_children = len(child_ids) > 0
        is_collapsed = sid in collapsed
        visible.append((depth, ts, msgs, name, sid, has_children, is_collapsed))

        if is_collapsed:
            skip_depth = depth

    return visible


def draw_tree(stdscr, rows, selected, scroll_offset, filter_text=None):
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    header = " SESSION TREE  (↑↓ navigate | ←→ collapse/expand | Enter resume | / search | q quit)"
    stdscr.attron(curses.color_pair(3))
    stdscr.addnstr(0, 0, header.ljust(width), width - 1)
    stdscr.attroff(curses.color_pair(3))

    if filter_text is not None:
        filter_line = f" Filter: {filter_text}█"
        stdscr.attron(curses.color_pair(4))
        stdscr.addnstr(1, 0, filter_line.ljust(width), width - 1)
        stdscr.attroff(curses.color_pair(4))
        content_start = 2
    else:
        content_start = 1

    visible_count = height - content_start - 2
    for i in range(visible_count):
        row_idx = i + scroll_offset
        if row_idx >= len(rows):
            break

        depth, ts, msgs, name, sid, has_children, is_collapsed = rows[row_idx]

        indent = "  " * depth
        if has_children:
            marker = "▸ " if is_collapsed else "▾ "
        else:
            marker = "  "

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

    if rows:
        _, _, _, _, sid, _, _ = rows[selected]
        footer = f" {sid}"
        stdscr.attron(curses.color_pair(3))
        stdscr.addnstr(height - 1, 0, footer.ljust(width), width - 1)
        stdscr.attroff(curses.color_pair(3))

    stdscr.refresh()


def main(stdscr, project_path):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)

    tree = build_tree_json(project_path)
    all_rows = build_full_rows(tree)

    if not all_rows:
        stdscr.addstr(0, 0, "No sessions found.")
        stdscr.getch()
        return None

    collapsed = set()
    rows = get_visible_rows(all_rows, collapsed)
    selected = 0
    scroll_offset = 0
    filter_text = None

    while True:
        height, width = stdscr.getmaxyx()
        content_start = 2 if filter_text is not None else 1
        visible = height - content_start - 2

        if selected < scroll_offset:
            scroll_offset = selected
        if selected >= scroll_offset + visible:
            scroll_offset = selected - visible + 1

        draw_tree(stdscr, rows, selected, scroll_offset, filter_text)
        key = stdscr.getch()

        if filter_text is not None:
            if key == 27:
                filter_text = None
                rows = get_visible_rows(all_rows, collapsed)
                selected = 0
                scroll_offset = 0
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                filter_text = filter_text[:-1]
                if not filter_text:
                    rows = get_visible_rows(all_rows, collapsed)
                else:
                    base = get_visible_rows(all_rows, collapsed)
                    rows = [r for r in base if filter_text.lower() in r[3].lower()]
                selected = min(selected, max(0, len(rows) - 1))
                scroll_offset = 0
            elif key == 10:
                filter_text = None
            elif 32 <= key <= 126:
                filter_text += chr(key)
                base = get_visible_rows(all_rows, collapsed)
                rows = [r for r in base if filter_text.lower() in r[3].lower()]
                selected = min(selected, max(0, len(rows) - 1))
                scroll_offset = 0
            continue

        if key == ord("q") or key == 27:
            return None
        elif key == curses.KEY_UP or key == ord("k"):
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            selected = min(len(rows) - 1, selected + 1)
        elif key == curses.KEY_LEFT or key == ord("h"):
            # Collapse: if has children and expanded, collapse it
            # If no children or already collapsed, jump to parent
            if rows:
                _, _, _, _, sid, has_children, is_collapsed = rows[selected]
                if has_children and not is_collapsed:
                    collapsed.add(sid)
                    rows = get_visible_rows(all_rows, collapsed)
                    selected = min(selected, len(rows) - 1)
                else:
                    # Jump to parent (find nearest row with lower depth)
                    cur_depth = rows[selected][0]
                    for i in range(selected - 1, -1, -1):
                        if rows[i][0] < cur_depth:
                            selected = i
                            break
        elif key == curses.KEY_RIGHT or key == ord("l"):
            # Expand: if collapsed, expand it
            if rows:
                _, _, _, _, sid, has_children, is_collapsed = rows[selected]
                if has_children and is_collapsed:
                    collapsed.discard(sid)
                    rows = get_visible_rows(all_rows, collapsed)
        elif key == curses.KEY_PPAGE:
            selected = max(0, selected - visible)
        elif key == curses.KEY_NPAGE:
            selected = min(len(rows) - 1, selected + visible)
        elif key == ord("g"):
            selected = 0
            scroll_offset = 0
        elif key == ord("G"):
            selected = len(rows) - 1
        elif key == ord("/"):
            filter_text = ""
        elif key == 10:
            if rows:
                _, _, _, _, sid, _, _ = rows[selected]
                return sid


def run(project_path=None):
    result = curses.wrapper(main, project_path)
    if result:
        os.execvp("claude", ["claude", "--resume", result])


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    run(path)
