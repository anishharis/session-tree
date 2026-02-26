# session-tree

A [Claude Code skill](https://code.claude.com/docs/en/skills) that visualizes your conversation history as a tree, showing fork relationships between sessions.

Claude Code stores conversations as JSONL files but provides no way to see how sessions relate to each other -- especially when you use `/fork` to branch conversations. This skill parses those files, detects fork relationships, and renders the result as a navigable tree.

## Demo

**ASCII output** (default):

```
├── Feb 12 06:20 (1183 msgs) Update my resume
│   ├── Feb 12 06:20 (202 msgs) Resume Fork 1
│   └── Feb 12 06:20 (282 msgs) Resume Fork 2
├── Feb 26 04:09 (80 msgs) GDrive folder research
│   ├── Feb 26 09:09 (242 msgs) CONTEXT:2026-02-26
│   ├── Feb 26 09:09 (229 msgs) GDrive Fork 2
│   └── Feb 26 09:09 (225 msgs) GDrive Fork 1
├── Feb 26 09:07 (3 msgs) in yazi how do i view dotfiles
└── Feb 26 10:18 (250 msgs) saving the transcript of claude cli chat
    └── Feb 26 10:18 (46 msgs) Transcript Fork
```

**Interactive TUI** (`-i` flag):

```
 SESSION TREE  (↑↓ navigate | Enter resume | / search | q quit)
▸ Feb 12 06:20 (1183) Update my resume
    Feb 12 06:20 (202) Resume Fork 1
    Feb 12 06:20 (282) Resume Fork 2
▸ Feb 26 04:09 (80) GDrive folder research
  > Feb 26 09:09 (242) CONTEXT:2026-02-26           <-- selected
    Feb 26 09:09 (229) GDrive Fork 2
    Feb 26 09:09 (225) GDrive Fork 1

 55a9dc1c-c6be-438d-a4ae-9b22e691defd
```

## Install

Clone into your Claude Code skills directory:

```bash
git clone https://github.com/anishharis/session-tree ~/.claude/skills/session-tree
```

That's it. The `/session-tree` slash command is now available in Claude Code.

## Usage

### As a Claude Code skill

```
/session-tree                    # full ASCII tree
/session-tree interactive        # interactive TUI browser
/session-tree resume             # subtree filtered to sessions matching "resume"
/session-tree --depth 0          # roots only, forks collapsed
/session-tree excalidraw         # render to Excalidraw (needs MCP server)
```

### As a standalone CLI

You can also run the scripts directly without Claude Code:

```bash
# ASCII tree for current project
python3 ~/.claude/skills/session-tree/scripts/build_tree.py \
  ~/.claude/projects/-Users-yourname-yourproject/

# Interactive browser
python3 ~/.claude/skills/session-tree/scripts/build_tree.py \
  ~/.claude/projects/-Users-yourname-yourproject/ -i

# Filter to a specific session subtree
python3 ~/.claude/skills/session-tree/scripts/build_tree.py \
  ~/.claude/projects/-Users-yourname-yourproject/ --filter "resume"

# JSON output (for piping to other tools)
python3 ~/.claude/skills/session-tree/scripts/build_tree.py \
  ~/.claude/projects/-Users-yourname-yourproject/ --json

# Limit tree depth
python3 ~/.claude/skills/session-tree/scripts/build_tree.py \
  ~/.claude/projects/-Users-yourname-yourproject/ --depth 1
```

### Finding your project path

Claude Code stores session data in `~/.claude/projects/` with directory names derived from your working directory by replacing `/` with `-`. For example:

| Working directory | Session directory |
|---|---|
| `/Users/alice/myproject` | `~/.claude/projects/-Users-alice-myproject/` |
| `/home/bob/code/api` | `~/.claude/projects/-home-bob-code-api/` |

## Interactive TUI keybindings

| Key | Action |
|---|---|
| `↑` / `k` | Move up |
| `↓` / `j` | Move down |
| `Enter` | Print resume command for selected session |
| `/` | Search/filter by session name |
| `Esc` | Cancel search or quit |
| `g` | Jump to top |
| `G` | Jump to bottom |
| `PgUp` / `PgDn` | Page up / down |
| `q` | Quit |

The footer bar always shows the full session UUID of the highlighted session. After pressing Enter, run the printed `claude --resume <id>` command to resume that session.

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

## License

MIT
