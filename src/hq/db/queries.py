import json
from datetime import datetime, timezone

from hq.db.models import get_db
from hq.config import get_stages, validate_stage


def add_entity(
    module: str,
    title: str,
    stage: str | None = None,
    assignee: str | None = None,
    description: str | None = None,
) -> dict:
    db = get_db()
    if stage is None:
        stage = get_stages(module)[0]
    if not validate_stage(module, stage):
        raise ValueError(f"Invalid stage '{stage}' for {module}. Valid: {', '.join(get_stages(module))}")

    row = {
        "title": title,
        "module": module,
        "stage": stage,
        "assignee": assignee,
        "description": description,
        "contacts": "[]",
    }
    result = db["entities"].insert(row)
    row["id"] = result.last_pk
    return row


def list_entities(
    module: str,
    stage: str | None = None,
    assignee: str | None = None,
) -> list[dict]:
    db = get_db()
    where_clauses = ["module = ?", "deleted_at IS NULL"]
    params: list = [module]

    if stage:
        where_clauses.append("stage = ?")
        params.append(stage)
    if assignee:
        where_clauses.append("assignee = ?")
        params.append(assignee)
    sql = f"SELECT * FROM entities WHERE {' AND '.join(where_clauses)} ORDER BY created_at DESC"
    rows = list(db.execute(sql, params).fetchall())
    columns = [d[0] for d in db.execute(sql, params).description] if rows else []

    return [dict(zip(columns, r)) for r in rows]


def get_entity(module: str, query: str) -> list[dict]:
    db = get_db()
    sql = """
        SELECT * FROM entities
        WHERE module = ? AND title LIKE ? COLLATE NOCASE AND deleted_at IS NULL
        ORDER BY created_at DESC
    """
    rows = list(db.execute(sql, [module, f"%{query}%"]).fetchall())
    if not rows:
        return []
    columns = [d[0] for d in db.execute(sql, [module, f"%{query}%"]).description]
    return [dict(zip(columns, r)) for r in rows]


def get_entity_one(module: str, query: str) -> dict | None:
    """Get a single entity by fuzzy match. Returns None if no match, raises if ambiguous."""
    matches = get_entity(module, query)
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(
            f"Multiple matches for '{query}': "
            + ", ".join(f"#{m['id']} {m['title']}" for m in matches)
            + ". Be more specific."
        )
    return matches[0]


def delete_entity(module: str, query: str) -> dict:
    entity = get_entity_one(module, query)
    if not entity:
        raise ValueError(f"No {module} entity matching '{query}'")
    db = get_db()
    db["entities"].update(entity["id"], {"deleted_at": datetime.now(timezone.utc).isoformat()})
    return entity


def edit_entity(module: str, query: str, **fields: str | None) -> dict:
    """Update arbitrary fields on an entity. Only non-None values are applied."""
    entity = get_entity_one(module, query)
    if not entity:
        raise ValueError(f"No {module} entity matching '{query}'")

    updates = {k: v for k, v in fields.items() if v is not None}
    if not updates:
        raise ValueError("No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    db = get_db()
    db["entities"].update(entity["id"], updates)
    entity.update(updates)
    return entity


def move_entity(module: str, query: str, stage: str) -> dict:
    if not validate_stage(module, stage):
        raise ValueError(f"Invalid stage '{stage}' for {module}. Valid: {', '.join(get_stages(module))}")

    entity = get_entity_one(module, query)
    if not entity:
        raise ValueError(f"No {module} entity matching '{query}'")

    db = get_db()
    db["entities"].update(entity["id"], {"stage": stage, "updated_at": datetime.now(timezone.utc).isoformat()})
    entity["stage"] = stage
    return entity


def move_entity_by_id(entity_id: int, stage: str) -> None:
    db = get_db()
    db["entities"].update(entity_id, {"stage": stage, "updated_at": datetime.now(timezone.utc).isoformat()})


def update_field(entity_id: int, field: str, value: str) -> dict:
    """Update a single field by entity ID. Used by TUI for direct edits."""
    db = get_db()
    db["entities"].update(entity_id, {field: value, "updated_at": datetime.now(timezone.utc).isoformat()})
    return {"id": entity_id, field: value}


# Contacts helpers (CRM)

def _get_contacts(entity: dict) -> list[dict]:
    return json.loads(entity.get("contacts") or "[]")


def _save_contacts(entity_id: int, contacts: list[dict]) -> None:
    db = get_db()
    db["entities"].update(entity_id, {
        "contacts": json.dumps(contacts),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


def add_contact(
    module: str,
    query: str,
    name: str,
    email: str | None = None,
    phone: str | None = None,
) -> dict:
    entity = get_entity_one(module, query)
    if not entity:
        raise ValueError(f"No {module} entity matching '{query}'")

    contacts = _get_contacts(entity)
    contact: dict[str, str] = {"name": name}
    if email:
        contact["email"] = email
    if phone:
        contact["phone"] = phone
    contacts.append(contact)
    _save_contacts(entity["id"], contacts)
    entity["contacts"] = json.dumps(contacts)
    return entity


def remove_contact(module: str, query: str, name: str) -> dict:
    entity = get_entity_one(module, query)
    if not entity:
        raise ValueError(f"No {module} entity matching '{query}'")

    contacts = _get_contacts(entity)
    original_len = len(contacts)
    contacts = [c for c in contacts if c["name"].lower() != name.lower()]
    if len(contacts) == original_len:
        raise ValueError(f"No contact named '{name}' on '{entity['title']}'")
    _save_contacts(entity["id"], contacts)
    entity["contacts"] = json.dumps(contacts)
    return entity


def search_all(query: str) -> list[dict]:
    db = get_db()
    pattern = f"%{query}%"
    sql = """
        SELECT * FROM entities
        WHERE deleted_at IS NULL
          AND (title LIKE ? COLLATE NOCASE
           OR contacts LIKE ? COLLATE NOCASE
           OR description LIKE ? COLLATE NOCASE)
        ORDER BY updated_at DESC
    """
    rows = list(db.execute(sql, [pattern] * 3).fetchall())
    if not rows:
        return []
    columns = [d[0] for d in db.execute(sql, [pattern] * 3).description]
    return [dict(zip(columns, r)) for r in rows]


def get_status_summary() -> dict[str, dict[str, int]]:
    db = get_db()
    sql = "SELECT module, stage, COUNT(*) as count FROM entities WHERE deleted_at IS NULL GROUP BY module, stage"
    rows = db.execute(sql).fetchall()
    summary: dict[str, dict[str, int]] = {}
    for module, stage, count in rows:
        if module not in summary:
            summary[module] = {}
        summary[module][stage] = count
    return summary
