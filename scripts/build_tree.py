#!/usr/bin/env python3
"""
Build a tree of Claude Code sessions, detecting forks by matching
first user prompts and message content overlap.

Outputs JSON describing the tree structure for visualization.
"""

import json
import os
import glob
import re
import sys
from collections import defaultdict
from datetime import datetime


def strip_xml_tags(text):
    """Remove XML/HTML tags and clean up prompt text for display."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_session_info(jsonl_path):
    """Extract key info from a session JSONL file."""
    info = {
        "sessionId": os.path.basename(jsonl_path).replace(".jsonl", ""),
        "path": jsonl_path,
        "size": os.path.getsize(jsonl_path),
        "mtime": os.path.getmtime(jsonl_path),
        "firstPrompt": "",
        "firstTimestamp": "",
        "lastTimestamp": "",
        "messageCount": 0,
        "userMessages": [],
        "version": "",
        "name": "",
    }

    user_msg_count = 0
    first_3_user_texts = []

    try:
        with open(jsonl_path) as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                if not info["version"] and d.get("version"):
                    info["version"] = d["version"]

                ts = d.get("timestamp", "")
                if ts:
                    if not info["firstTimestamp"]:
                        info["firstTimestamp"] = ts
                    info["lastTimestamp"] = ts

                if d.get("type") == "user":
                    info["messageCount"] += 1
                    content = d.get("message", {}).get("content", "")
                    text = ""
                    if isinstance(content, list) and content:
                        text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
                    elif isinstance(content, str):
                        text = content

                    text = strip_xml_tags(text)

                    if not info["firstPrompt"] and text.strip():
                        info["firstPrompt"] = text.strip()

                    if len(first_3_user_texts) < 3 and text.strip():
                        first_3_user_texts.append(text.strip()[:200])

                elif d.get("type") == "assistant":
                    info["messageCount"] += 1

                # Check for custom title (set by /rename)
                if d.get("type") == "custom-title" and d.get("customTitle"):
                    info["name"] = d["customTitle"]

    except Exception as e:
        pass

    info["userMessages"] = first_3_user_texts
    return info


def detect_forks(sessions):
    """
    Detect fork relationships between sessions.
    A fork shares the same first prompt and has a later start time.
    """
    # Group by first prompt
    by_prompt = defaultdict(list)
    for s in sessions:
        prompt = s["firstPrompt"]
        if prompt:
            by_prompt[prompt].append(s)

    # For groups with multiple sessions, the earliest is the root
    edges = []  # (parent_id, child_id)
    roots = set()

    for prompt, group in by_prompt.items():
        if len(group) < 2:
            roots.add(group[0]["sessionId"])
            continue

        # Sort by start time - earliest is the root
        group.sort(key=lambda x: x["firstTimestamp"])
        root = group[0]
        roots.add(root["sessionId"])

        for child in group[1:]:
            edges.append((root["sessionId"], child["sessionId"]))

    # Sessions with unique prompts are standalone roots
    for s in sessions:
        if s["sessionId"] not in roots and not any(
            c == s["sessionId"] for _, c in edges
        ):
            roots.add(s["sessionId"])

    return edges, roots


def format_timestamp(ts_str):
    """Format ISO timestamp to readable form."""
    if not ts_str:
        return "?"
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d %H:%M")
    except:
        return ts_str[:16]


def build_tree_json(project_path=None):
    """Build the full session tree for a project."""
    if not project_path:
        # Auto-detect from cwd
        cwd = os.getcwd()
        encoded = re.sub(r"[/.]", "-", cwd)
        project_path = os.path.expanduser(f"~/.claude/projects/{encoded}/")

    jsonl_files = glob.glob(os.path.join(project_path, "*.jsonl"))

    sessions = []
    for f in jsonl_files:
        info = get_session_info(f)
        if info["messageCount"] > 0:  # Skip empty sessions
            sessions.append(info)

    # Sort by creation time
    sessions.sort(key=lambda x: x["firstTimestamp"])

    edges, roots = detect_forks(sessions)

    # Build adjacency list
    children = defaultdict(list)
    for parent, child in edges:
        children[parent].append(child)

    session_map = {s["sessionId"]: s for s in sessions}

    return {
        "sessions": session_map,
        "edges": edges,
        "roots": sorted(roots, key=lambda r: session_map.get(r, {}).get("firstTimestamp", "")),
        "children": dict(children),
    }


def print_ascii_tree(tree_data, max_depth=None):
    """Print an ASCII tree representation."""
    session_map = tree_data["sessions"]
    children = tree_data["children"]
    roots = tree_data["roots"]

    def print_node(sid, prefix="", is_last=True, depth=0):
        if max_depth is not None and depth > max_depth:
            return
        s = session_map.get(sid, {})
        connector = "└── " if is_last else "├── "
        raw_name = s.get("name") or s.get("firstPrompt", "") or "(no prompt)"
        name = raw_name
        ts = format_timestamp(s.get("firstTimestamp", ""))
        msgs = s.get("messageCount", 0)

        # Truncate name so the line fits in ~100 chars
        meta = f"{prefix}{connector}{ts} ({msgs} msgs) "
        max_name = max(20, 100 - len(meta))
        if len(name) > max_name:
            name = name[:max_name - 1] + "…"

        print(f"{prefix}{connector}{ts} ({msgs} msgs) {name}")

        child_ids = children.get(sid, [])
        child_ids.sort(key=lambda c: session_map.get(c, {}).get("firstTimestamp", ""))

        if max_depth is not None and depth + 1 > max_depth and child_ids:
            new_prefix = prefix + ("    " if is_last else "│   ")
            print(f"{new_prefix}└── ... {len(child_ids)} fork(s)")
            return

        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(child_ids):
            print_node(child, new_prefix, i == len(child_ids) - 1, depth + 1)

    for i, root in enumerate(roots):
        is_last_root = i == len(roots) - 1
        print_node(root, "", is_last_root, depth=0)

    print()
    print("Resume: claude --resume \"<keyword>\"")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code session tree visualizer")
    parser.add_argument("project_path", nargs="?", help="Path to Claude project directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--depth", type=int, default=None, help="Max tree depth to display")
    parser.add_argument("--filter", type=str, default=None, help="Show only tree rooted at session matching keyword")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive tree browser")
    args = parser.parse_args()

    tree = build_tree_json(args.project_path)

    if args.filter:
        keyword = args.filter.lower()
        # Find matching session
        match = None
        for sid, s in tree["sessions"].items():
            name = s.get("name") or s.get("firstPrompt", "")
            if keyword in name.lower() or keyword in sid.lower():
                match = sid
                break
        if match:
            # Collect this node and all its descendants
            def collect_subtree(sid):
                result = {sid}
                for child in tree["children"].get(sid, []):
                    result |= collect_subtree(child)
                return result

            keep = collect_subtree(match)
            tree["roots"] = [match]
            tree["children"] = {k: v for k, v in tree["children"].items() if k in keep}
            tree["sessions"] = {k: v for k, v in tree["sessions"].items() if k in keep}
            tree["edges"] = [(p, c) for p, c in tree["edges"] if p in keep and c in keep]
        else:
            print(f"No session matching \"{args.filter}\"")
            sys.exit(1)

    if args.interactive:
        from interactive_tree import run
        run(args.project_path)
    elif args.json:
        output = {
            "edges": tree["edges"],
            "roots": tree["roots"],
            "children": tree["children"],
            "sessions": {
                sid: {k: v for k, v in s.items() if k != "path"}
                for sid, s in tree["sessions"].items()
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print_ascii_tree(tree, max_depth=args.depth)
