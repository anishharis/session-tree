---
name: session-tree
description: |
  Visualize Claude Code session history as a tree showing fork relationships.
  Use when: "show session tree", "session tree", "show my forks", "visualize conversations",
  "conversation tree", "session history tree", "chat tree"
disable-model-invocation: true
allowed-tools: Bash(python3 *), mcp__excalidraw__create_element, mcp__excalidraw__batch_create_elements, mcp__excalidraw__create_from_mermaid, mcp__excalidraw__query_elements, Read
argument-hint: "[keyword] [ascii|interactive|excalidraw] [--depth N]"
---

# Session Tree Visualizer

Visualize Claude Code session history as a tree, showing fork relationships between sessions.

## How to use

1. Run the tree builder script to get session data:

```bash
python3 ~/.claude/skills/session-tree/scripts/build_tree.py "$PROJECT_DIR"
```

Where `$PROJECT_DIR` is the Claude project directory, typically:
`~/.claude/projects/-Users-<username>-<project-path>/`

The current project path can be derived from the cwd by replacing `/` with `-`.

2. Based on the argument `$ARGUMENTS`:

### Keyword filter
If the user provides a keyword (e.g. `/session-tree resume`), pass it as `--filter "keyword"` to the script. This shows only the subtree rooted at the matching session.

### `ascii` (default)
Just run the script with no flags — it outputs an ASCII tree to the terminal. Show the output to the user.

### `interactive`
Run the script with `-i` flag. This launches a curses-based TUI where the user can:
- ↑↓ / j/k to navigate
- Enter to select a session and get its resume command
- / to search/filter by name
- g/G to jump to top/bottom
- q or Esc to quit
The footer shows the full session UUID of the highlighted session.

### `excalidraw`
Run the script with `--json` flag to get structured data, then use the Excalidraw MCP tools to render the tree visually:
- Use `mcp__excalidraw__batch_create_elements` to create rectangles for each session node
- Use arrows to connect parent → child forks
- Color-code: blue for root sessions, green for forks
- Include session summary, timestamp, and message count in each node

### `mermaid`
Run the script with `--json` flag, then construct a Mermaid graph definition and use `mcp__excalidraw__create_from_mermaid` to render it.

## Fork detection
The script detects forks by matching sessions that share the same first user prompt. The earliest session with a given prompt is treated as the root, and later sessions with the same prompt are forks.
