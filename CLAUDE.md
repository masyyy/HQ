# HQ -- Company OS CLI

## What is HQ?

HQ is a CLI-first company operating system for small teams. It replaces bloated SaaS tools
(Linear, HubSpot) with a single local tool. Two modules:

- **Board** -- product work: features, bugs, tasks
- **CRM** -- sales pipeline: companies, contacts, deals

All data lives locally in SQLite. No accounts, no cloud, no subscriptions.

## Design Philosophy

There are two interfaces and they serve different audiences:

**CLI (agent-first):** Output is plain text, minimal, token-efficient. No Rich tables, no
color markup, no decorative borders. Designed to be driven by AI agents (Claude Code, etc.)
and parsed programmatically. Being agent-friendly also means being human-friendly -- clear
help text, consistent command patterns, predictable output format.

**TUI (human-first):** The Textual-based interface is where visual richness belongs. Kanban
boards, color, ASCII art banner, interactive navigation. This is the graphical layer for
humans who want to browse and manage visually.

Keep this separation strict. CLI commands should never waste tokens on presentation.

## Project Layout

```
src/hq/
  main.py          Typer app, global commands (status, search, tui)
  config.py        TOML config (~/.hq/config.toml), stage management
  cli/
    common.py      Plain text rendering for list/show output
    board.py       board subcommands: add, list, show, move, edit
    crm.py         crm subcommands: add, list, show, move, edit, add-contact, remove-contact, contacts
  db/
    models.py      SQLite schema, get_db() singleton
    queries.py     All CRUD: add/list/get/move/edit/search + contact helpers
  tui/
    app.py         Textual App, module switching, kanban navigation
    kanban.py      KanbanBoard, KanbanColumn, Card widgets
    detail.py      DetailScreen modal with editable title/description
    banner.py      pyfiglet ASCII banner
```

## Data

- **Database:** `~/.hq/hq.db` -- single `entities` table
- **Config:** `~/.hq/config.toml` -- custom stages per module
- Contacts stored as JSON array: `[{"name": "...", "email": "...", "phone": "..."}]`
- Description is plain text
- Soft deletes via `deleted_at` column -- all queries filter `deleted_at IS NULL`
- Fuzzy match via `LIKE '%query%' COLLATE NOCASE`

## Commands

```bash
# Board
hq board add "Title" -d "Description" -a assignee
hq board list [--stage X] [--assignee X]
hq board show "query"
hq board move "query" stage
hq board edit "query" [-t title] [-a assignee] [-d description]
hq board delete "query"

# CRM
hq crm add "Company" -d "Description"
hq crm list [--stage X] [--assignee X]
hq crm show "query"
hq crm move "query" stage
hq crm edit "query" [-t title] [-a assignee] [-d description]
hq crm add-contact "query" "Name" [-e email] [-p phone]
hq crm remove-contact "query" "Name"
hq crm contacts "query"
hq crm delete "query"

# Global
hq status              Cross-module summary (one line per module)
hq search "query"      Full-text search across all modules
hq tui                 Launch TUI
```

## Development

```bash
cd hq-cli
uv run hq --help
uv run hq board add "Test item"
```

## Database Migrations

HQ is used in production. All schema changes must be done via migrations -- never drop/recreate
tables or make destructive changes that would lose data.

## Key Patterns

- Both modules share: add, list, show, move, edit, delete
- CRM adds contact management: add-contact, remove-contact, contacts
- Errors go to stderr, normal output to stdout
- Multiple fuzzy matches prompt the user to be more specific (no silent ambiguity)
- DB uses a singleton connection per process to avoid locking issues
- TUI is lazy-imported so Textual doesn't load for CLI calls
- TUI key handling: app-level `on_key` intercepts during move mode; screen stack
  handles DetailScreen bindings (escape, j/k, enter) without conflicting with app bindings
