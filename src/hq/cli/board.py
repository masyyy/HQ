import sys
from typing import Optional

import typer

from hq.cli.common import render_entity_table, render_entity_detail
from hq.db.queries import add_entity, list_entities, get_entity_one, move_entity, edit_entity, delete_entity, reorder_entity

board_app = typer.Typer(help="Product board -- features, bugs, tasks.")

MODULE = "board"


@board_app.command()
def add(
    title: str = typer.Argument(..., help="Title of the board item"),
    stage: Optional[str] = typer.Option(None, "-s", "--stage", help="Stage (default: backlog)"),
    assignee: Optional[str] = typer.Option(None, "-a", "--assignee", help="Assignee"),
    description: Optional[str] = typer.Option(None, "-d", "--description", help="Description"),
) -> None:
    """Add a new board item."""
    try:
        entity = add_entity(MODULE, title, stage=stage, assignee=assignee, description=description)
        print(f"Created board item #{entity['id']}: {title}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@board_app.command("list")
def list_cmd(
    stage: Optional[str] = typer.Option(None, "-s", "--stage", help="Filter by stage"),
    assignee: Optional[str] = typer.Option(None, "-a", "--assignee", help="Filter by assignee"),
) -> None:
    """List board items grouped by stage."""
    entities = list_entities(MODULE, stage=stage, assignee=assignee)
    render_entity_table(entities, MODULE)


@board_app.command()
def show(query: str = typer.Argument(..., help="Fuzzy search for item by title")) -> None:
    """Show detail view of a board item."""
    try:
        entity = get_entity_one(MODULE, query)
        if not entity:
            print(f"No board item matching '{query}'", file=sys.stderr)
            raise typer.Exit(1)
        render_entity_detail(entity)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@board_app.command()
def move(
    query: str = typer.Argument(..., help="Item to move (fuzzy match)"),
    stage: str = typer.Argument(..., help="Target stage"),
) -> None:
    """Move a board item to a different stage."""
    try:
        entity = move_entity(MODULE, query, stage)
        print(f"Moved '{entity['title']}' -> {stage}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@board_app.command()
def edit(
    query: str = typer.Argument(..., help="Item to edit (fuzzy match)"),
    title: Optional[str] = typer.Option(None, "-t", "--title", help="New title"),
    assignee: Optional[str] = typer.Option(None, "-a", "--assignee", help="New assignee"),
    description: Optional[str] = typer.Option(None, "-d", "--description", help="New description"),
) -> None:
    """Edit a board item's fields."""
    try:
        entity = edit_entity(MODULE, query, title=title, assignee=assignee, description=description)
        print(f"Updated '{entity['title']}'")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@board_app.command()
def delete(
    query: str = typer.Argument(..., help="Item to delete (fuzzy match)"),
) -> None:
    """Delete a board item."""
    try:
        entity = delete_entity(MODULE, query)
        print(f"Deleted '{entity['title']}'")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@board_app.command()
def prioritize(
    query: str = typer.Argument(..., help="Item to reorder (fuzzy match)"),
    direction: str = typer.Argument(..., help="up, down, top, or bottom"),
) -> None:
    """Reorder a board item within its current stage."""
    try:
        entity = reorder_entity(MODULE, query, direction)
        print(f"Moved '{entity['title']}' {direction}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
