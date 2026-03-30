import sys
import json
from typing import Optional

import typer

from hq.cli.common import render_entity_table, render_entity_detail
from hq.db.queries import (
    add_entity, list_entities, get_entity_one, move_entity, edit_entity,
    delete_entity, add_contact, remove_contact, reorder_entity,
)

crm_app = typer.Typer(help="CRM -- sales pipeline, contacts, deals.")

MODULE = "crm"


@crm_app.command()
def add(
    title: str = typer.Argument(..., help="Company or deal name"),
    stage: Optional[str] = typer.Option(None, "-s", "--stage", help="Stage (default: lead)"),
    assignee: Optional[str] = typer.Option(None, "-a", "--assignee", help="Assignee"),
    description: Optional[str] = typer.Option(None, "-d", "--description", help="Description"),
) -> None:
    """Add a new CRM entry."""
    try:
        entity = add_entity(MODULE, title, stage=stage, assignee=assignee, description=description)
        print(f"Created CRM entry #{entity['id']}: {title}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@crm_app.command("list")
def list_cmd(
    stage: Optional[str] = typer.Option(None, "-s", "--stage", help="Filter by stage"),
    assignee: Optional[str] = typer.Option(None, "-a", "--assignee", help="Filter by assignee"),
) -> None:
    """List CRM entries grouped by stage."""
    entities = list_entities(MODULE, stage=stage, assignee=assignee)
    render_entity_table(entities, MODULE)


@crm_app.command()
def show(query: str = typer.Argument(..., help="Fuzzy search by name")) -> None:
    """Show detail view of a CRM entry."""
    try:
        entity = get_entity_one(MODULE, query)
        if not entity:
            print(f"No CRM entry matching '{query}'", file=sys.stderr)
            raise typer.Exit(1)
        render_entity_detail(entity)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@crm_app.command()
def move(
    query: str = typer.Argument(..., help="Entry to move (fuzzy match)"),
    stage: str = typer.Argument(..., help="Target stage"),
) -> None:
    """Move a CRM entry to a different stage."""
    try:
        entity = move_entity(MODULE, query, stage)
        print(f"Moved '{entity['title']}' -> {stage}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@crm_app.command()
def edit(
    query: str = typer.Argument(..., help="Entry to edit (fuzzy match)"),
    title: Optional[str] = typer.Option(None, "-t", "--title", help="New title"),
    assignee: Optional[str] = typer.Option(None, "-a", "--assignee", help="New assignee"),
    description: Optional[str] = typer.Option(None, "-d", "--description", help="New description"),
) -> None:
    """Edit a CRM entry's fields."""
    try:
        entity = edit_entity(MODULE, query, title=title, assignee=assignee, description=description)
        print(f"Updated '{entity['title']}'")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@crm_app.command()
def delete(
    query: str = typer.Argument(..., help="Entry to delete (fuzzy match)"),
) -> None:
    """Delete a CRM entry."""
    try:
        entity = delete_entity(MODULE, query)
        print(f"Deleted '{entity['title']}'")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@crm_app.command()
def prioritize(
    query: str = typer.Argument(..., help="Entry to reorder (fuzzy match)"),
    direction: str = typer.Argument(..., help="up, down, top, or bottom"),
) -> None:
    """Reorder a CRM entry within its current stage."""
    try:
        entity = reorder_entity(MODULE, query, direction)
        print(f"Moved '{entity['title']}' {direction}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@crm_app.command("add-contact")
def add_contact_cmd(
    query: str = typer.Argument(..., help="CRM entry (fuzzy match)"),
    name: str = typer.Argument(..., help="Contact name"),
    email: Optional[str] = typer.Option(None, "-e", "--email", help="Email address"),
    phone: Optional[str] = typer.Option(None, "-p", "--phone", help="Phone number"),
) -> None:
    """Add a contact to a CRM entry."""
    try:
        entity = add_contact(MODULE, query, name, email=email, phone=phone)
        print(f"Added contact '{name}' to '{entity['title']}'")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@crm_app.command("remove-contact")
def remove_contact_cmd(
    query: str = typer.Argument(..., help="CRM entry (fuzzy match)"),
    name: str = typer.Argument(..., help="Contact name to remove"),
) -> None:
    """Remove a contact from a CRM entry."""
    try:
        entity = remove_contact(MODULE, query, name)
        print(f"Removed contact '{name}' from '{entity['title']}'")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@crm_app.command("contacts")
def contacts_cmd(
    query: str = typer.Argument(..., help="CRM entry (fuzzy match)"),
) -> None:
    """List contacts on a CRM entry."""
    try:
        entity = get_entity_one(MODULE, query)
        if not entity:
            print(f"No CRM entry matching '{query}'", file=sys.stderr)
            raise typer.Exit(1)
        contacts = json.loads(entity.get("contacts") or "[]")
        if not contacts:
            print(f"No contacts on '{entity['title']}'")
            return
        for c in contacts:
            parts = [c["name"]]
            if c.get("email"):
                parts.append(c["email"])
            if c.get("phone"):
                parts.append(c["phone"])
            print("  " + " | ".join(parts))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
