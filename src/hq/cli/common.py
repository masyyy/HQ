import json

from hq.config import get_stages


def _format_contacts_short(contacts_json: str) -> str:
    """Format contacts for list view — just names."""
    contacts = json.loads(contacts_json or "[]")
    if not contacts:
        return ""
    return ", ".join(c["name"] for c in contacts)


def render_entity_table(entities: list[dict], module: str) -> None:
    if not entities:
        print(f"No {module} items found.")
        return

    stages = get_stages(module)
    grouped: dict[str, list[dict]] = {s: [] for s in stages}
    for e in entities:
        if e["stage"] in grouped:
            grouped[e["stage"]].append(e)

    for stage, items in grouped.items():
        if not items:
            continue

        print(f"\n{stage.upper()}")

        for e in items:
            parts = [str(e["id"]), e["title"]]
            if module == "crm":
                contacts = _format_contacts_short(e.get("contacts", "[]"))
                if contacts:
                    parts.append(contacts)

            print("  " + " | ".join(parts))


def render_entity_detail(entity: dict) -> None:
    print(f"\n{entity['title']}")
    print(f"  id: {entity['id']}")
    print(f"  module: {entity['module']}")
    print(f"  stage: {entity['stage']}")

    if entity.get("assignee"):
        print(f"  assignee: {entity['assignee']}")

    contacts = json.loads(entity.get("contacts") or "[]")
    if contacts:
        print("  contacts:")
        for c in contacts:
            parts = [c["name"]]
            if c.get("email"):
                parts.append(c["email"])
            if c.get("phone"):
                parts.append(c["phone"])
            print(f"    {' | '.join(parts)}")

    if entity.get("description"):
        print(f"  description: {entity['description']}")

    print(f"  created: {entity['created_at']}")
    print(f"  updated: {entity['updated_at']}")
