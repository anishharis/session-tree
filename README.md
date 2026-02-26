# session-tree

![GitHub stars](https://img.shields.io/github/stars/anishharis/session-tree?style=flat-square)
![GitHub forks](https://img.shields.io/github/forks/anishharis/session-tree?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/anishharis/session-tree?style=flat-square)
![GitHub repo size](https://img.shields.io/github/repo-size/anishharis/session-tree?style=flat-square)

A [Claude Code skill](https://code.claude.com/docs/en/skills) that visualizes your conversation history as a tree, showing fork relationships between sessions.

Claude Code stores conversations as JSONL files but provides no way to see how sessions relate to each other -- especially when you use `/fork` to branch conversations. This skill parses those files, detects fork relationships, and renders the result as a navigable tree.

**Highly recommended:** Use `/rename` in your sessions to give them meaningful names. The tree displays custom names when set, and they're searchable with `claude --resume`. Without renaming, you'll see a wall of truncated first prompts that all look the same (especially forks).

```
/rename Auth refactor exploration
/rename PRODUCTION-SCHEMA
/rename Stripe integration attempt
```

## Demo

**ASCII output** (default):

```
├── Mar 01 09:15 (42 msgs) Set up Express API with auth middleware
├── Mar 01 14:30 (18 msgs) Fix CORS issue on /api/users endpoint
├── Mar 02 10:00 (156 msgs) Implement payment integration
│   └── Mar 02 11:45 (89 msgs) Stripe approach
│       └── Mar 02 12:30 (134 msgs) Stripe with webhooks
│           ├── Mar 02 14:00 (67 msgs) Webhooks v1
│           └── Mar 02 14:00 (92 msgs) FINAL: Stripe webhooks v2
├── Mar 03 08:20 (7 msgs) Add rate limiting to API
├── Mar 04 16:00 (210 msgs) Refactor database schema
│   └── Mar 04 18:30 (95 msgs) Schema v2 normalized
│       ├── Mar 04 19:00 (64 msgs) Normalize + add indexes
│       └── Mar 04 19:00 (112 msgs) PRODUCTION SCHEMA
├── Mar 05 09:00 (34 msgs) Write integration tests for checkout flow
├── Mar 05 13:45 (12 msgs) Debug flaky CI pipeline
└── Mar 06 10:30 (88 msgs) Deploy to staging

Resume: claude --resume "<keyword>"   (don't forget the quotes!)
```

**Interactive TUI** (`-i` flag):

```
 SESSION TREE  (↑↓ navigate | ←→ collapse/expand | Enter resume | / search | q quit)
  ▸ Mar 02 10:00 (156) Implement payment integration       ← collapsed (→ to expand)
    Mar 03 08:20 (7) Add rate limiting to API
  ▾ Mar 04 16:00 (210) Refactor database schema            ← expanded
    ▾ Mar 04 18:30 (95) Schema v2 normalized
        Mar 04 19:00 (64) Normalize + add indexes
        Mar 04 19:00 (112) PRODUCTION SCHEMA            ◀ selected
    Mar 05 09:00 (34) Write integration tests for checkout flow

 a3f8c21e-9b4d-4a17-b562-1e8f3d9c7a05
```

## Install

Clone into your Claude Code skills directory:

```bash
git clone https://github.com/anishharis/session-tree ~/.claude/skills/session-tree
```

That's it. The `/session-tree` slash command is now available in Claude Code.

## Set up the `stree` alias (recommended)

Add this to your `~/.zshrc` or `~/.bashrc`:

```bash
alias stree="python3 ~/.claude/skills/session-tree/scripts/build_tree.py"
```

The script auto-detects the Claude project path from your current working directory, so you don't need to pass any paths. Just `cd` into your project and run:

```bash
stree                       # ASCII tree
stree -i                    # interactive TUI — navigate with arrow keys, Enter to resume
stree --filter "auth"       # subtree matching "auth"
stree --depth 0             # roots only, forks collapsed
stree --json                # JSON output for piping to other tools
```

The interactive TUI (`stree -i`) is the best way to browse sessions. Press Enter on any session to immediately resume it with `claude --resume`.

## Usage

### As a Claude Code skill (because I like making skills)

```
/session-tree                    # full ASCII tree
/session-tree interactive        # get the command to launch the TUI (can't run inside Claude Code)
/session-tree payment            # only show the subtree matching "payment"
/session-tree --depth 0          # roots only, forks collapsed
/session-tree excalidraw         # render to Excalidraw (needs MCP server)
```

The ASCII tree shows session names you can copy-paste to resume:

```bash
claude --resume "Fix CORS issue"
claude --resume "payment"
```

The quotes matter — they let `claude --resume` fuzzy-match the session by name instead of requiring a UUID.

### As a standalone CLI

You can also run the scripts directly without the alias:

```bash
# ASCII tree for current project (auto-detects path from cwd)
python3 ~/.claude/skills/session-tree/scripts/build_tree.py

# Interactive browser
python3 ~/.claude/skills/session-tree/scripts/build_tree.py -i

# Filter to a specific session subtree
python3 ~/.claude/skills/session-tree/scripts/build_tree.py --filter "payment"

# JSON output (for piping to other tools)
python3 ~/.claude/skills/session-tree/scripts/build_tree.py --json

# Limit tree depth
python3 ~/.claude/skills/session-tree/scripts/build_tree.py --depth 1

# Explicit project path (if auto-detect doesn't work)
python3 ~/.claude/skills/session-tree/scripts/build_tree.py \
  ~/.claude/projects/-Users-yourname-yourproject/
```

## Interactive TUI keybindings

| Key | Action |
|---|---|
| `↑` / `k` | Move up |
| `↓` / `j` | Move down |
| `←` / `h` | Collapse node (or jump to parent) |
| `→` / `l` | Expand collapsed node |
| `Enter` | Immediately launch `claude --resume` for the selected session |
| `/` | Search/filter by session name |
| `Esc` | Cancel search or quit |
| `g` | Jump to top |
| `G` | Jump to bottom |
| `PgUp` / `PgDn` | Page up / down |
| `q` | Quit |

The footer bar always shows the full session UUID of the highlighted session. Pressing Enter exits the TUI and automatically runs `claude --resume <session-id>`, dropping you straight into that session.

## How fork detection works

Claude Code doesn't store fork parent-child relationships in its session metadata. When you `/fork` a conversation, the new session is created as a completely independent JSONL file with no link back to the original.

This skill works around that limitation by detecting forks heuristically:

1. Parse every `*.jsonl` file in the project directory
2. Extract each session's first user prompt (after stripping XML tags from system wrappers)
3. Group sessions that share an identical first prompt
4. Within each group, the earliest session (by timestamp) is treated as the root; later sessions are forks
5. Sessions renamed via `/rename` display their custom title instead of the first prompt

This approach works because `/fork` clones the conversation, so the forked session starts with the same first message as the original.

### Limitations

- Sessions that were `/fork`ed and then had their first message edited won't be detected as forks
- Sessions started independently with the same opening message will be falsely grouped as forks
- There's no way to detect which specific message in the parent session the fork branched from

## CLI flags reference

| Flag | Description |
|---|---|
| `<project_path>` | Path to the Claude project directory (auto-detects from cwd if omitted) |
| `-i`, `--interactive` | Launch the interactive curses TUI |
| `--filter <keyword>` | Show only the subtree rooted at the first session matching the keyword |
| `--depth <N>` | Limit tree rendering depth (0 = roots only) |
| `--json` | Output the full tree as JSON (for piping to other tools) |

## JSON output format

With `--json`, the script outputs:

```json
{
  "edges": [["parent-uuid", "child-uuid"], ...],
  "roots": ["uuid", ...],
  "children": {"parent-uuid": ["child-uuid", ...], ...},
  "sessions": {
    "uuid": {
      "sessionId": "uuid",
      "firstPrompt": "...",
      "firstTimestamp": "2026-01-31T10:57:00.000Z",
      "lastTimestamp": "2026-01-31T11:30:00.000Z",
      "messageCount": 57,
      "name": "custom title if renamed",
      "userMessages": ["first 3 user messages..."]
    }
  }
}
```

## Requirements

- Python 3.8+
- No external dependencies (uses only stdlib: `json`, `os`, `glob`, `re`, `curses`, `argparse`)
- Claude Code (for the skill integration; the scripts work standalone too)

## File structure

```
session-tree/
  SKILL.md                      # Claude Code skill definition
  scripts/
    build_tree.py               # Core tree builder + ASCII renderer + CLI
    interactive_tree.py          # Curses-based interactive TUI
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=anishharis/session-tree&type=Date)](https://star-history.com/#anishharis/session-tree&Date)

## License

MIT
