import json

from textual.app import ComposeResult
from textual.containers import HorizontalScroll, VerticalScroll
from textual.widgets import Static
from textual.reactive import reactive
from textual.message import Message

from hq.config import get_stages
from hq.db.queries import list_entities


class Card(Static, can_focus=True):
    """A single kanban card representing an entity."""

    DEFAULT_CSS = """
    Card {
        width: 100%;
        height: auto;
        min-height: 3;
        margin: 0 0 1 0;
        padding: 0 1;
        background: $surface;
        border: round $primary-background;
    }

    Card:focus {
        border: round $accent;
        background: $surface-lighten-1;
    }

    Card:hover {
        border: round $accent;
    }
    """

    class Selected(Message):
        """Posted when a card is selected (enter pressed)."""
        def __init__(self, entity: dict) -> None:
            self.entity = entity
            super().__init__()

    def __init__(self, entity: dict) -> None:
        self.entity = entity
        super().__init__()

    def compose(self) -> ComposeResult:
        e = self.entity

        title_line = f"[bold]{e['title']}[/bold]"

        detail_parts = []
        contacts = json.loads(e.get("contacts") or "[]")
        if contacts:
            detail_parts.append(", ".join(c["name"] for c in contacts))
        if e.get("assignee"):
            detail_parts.append(f"@{e['assignee']}")

        content = title_line
        if detail_parts:
            content += f"\n[dim]{' | '.join(detail_parts)}[/dim]"

        yield Static(content)

    def key_enter(self) -> None:
        self.post_message(self.Selected(self.entity))


class KanbanColumn(VerticalScroll):
    """A single stage column in the kanban board."""

    DEFAULT_CSS = """
    KanbanColumn {
        width: 1fr;
        min-width: 28;
        height: 100%;
        margin: 0 1;
        padding: 0;
    }
    """

    def __init__(self, stage: str, entities: list[dict]) -> None:
        self.stage = stage
        self.entities = entities
        super().__init__()

    def compose(self) -> ComposeResult:
        count = len(self.entities)
        count_str = f" ({count})" if count else ""
        yield Static(
            f"[bold underline]{self.stage.upper()}{count_str}[/bold underline]\n",
            classes="column-header",
        )
        for entity in self.entities:
            yield Card(entity)
        if not self.entities:
            yield Static("[dim italic]  empty[/dim italic]")


class KanbanBoard(HorizontalScroll):
    """A kanban board for a single module showing all stages as columns."""

    DEFAULT_CSS = """
    KanbanBoard {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    """

    module: reactive[str] = reactive("board")

    def __init__(self, module: str, id: str | None = None) -> None:
        super().__init__(id=id)
        self.module = module

    def compose(self) -> ComposeResult:
        stages = get_stages(self.module)
        entities = list_entities(self.module)

        grouped: dict[str, list[dict]] = {s: [] for s in stages}
        for e in entities:
            if e["stage"] in grouped:
                grouped[e["stage"]].append(e)

        for stage in stages:
            yield KanbanColumn(stage, grouped[stage])

    def refresh_board(self) -> None:
        """Reload data and rebuild the board."""
        self.remove_children()
        stages = get_stages(self.module)
        entities = list_entities(self.module)

        grouped: dict[str, list[dict]] = {s: [] for s in stages}
        for e in entities:
            if e["stage"] in grouped:
                grouped[e["stage"]].append(e)

        for stage in stages:
            self.mount(KanbanColumn(stage, grouped[stage]))
