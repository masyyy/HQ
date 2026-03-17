from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static, TextArea, Input
from textual.binding import Binding
from textual.message import Message

import json

from hq.db.queries import update_field


MODULE_COLORS = {
    "crm": "cyan",
    "board": "green",
}


class EditableField(Static, can_focus=True):
    """A field that can be selected with enter to edit."""

    DEFAULT_CSS = """
    EditableField {
        width: 100%;
        height: auto;
        min-height: 1;
        padding: 0 1;
    }

    EditableField:focus {
        background: $surface-lighten-1;
        text-style: bold;
    }
    """

    class Activated(Message):
        """Posted when the user presses enter on this field."""
        def __init__(self, field: "EditableField") -> None:
            self.field = field
            super().__init__()

    def __init__(self, label: str, value: str, field_id: str) -> None:
        self.label = label
        self.value = value
        super().__init__(id=field_id)
        self._render_display()

    def _render_display(self) -> None:
        if self.value:
            self.update(f"[bold]{self.label}:[/bold] {self.value}")
        else:
            self.update(f"[bold]{self.label}:[/bold] [dim italic]empty -- press enter to edit[/dim italic]")

    def key_enter(self) -> None:
        self.post_message(self.Activated(self))


class DescriptionField(Static, can_focus=True):
    """A multiline description field that can be selected with enter to edit."""

    DEFAULT_CSS = """
    DescriptionField {
        width: 100%;
        height: auto;
        min-height: 3;
        padding: 0 1;
    }

    DescriptionField:focus {
        background: $surface-lighten-1;
    }
    """

    class Activated(Message):
        """Posted when the user presses enter on this field."""
        def __init__(self, field: "DescriptionField") -> None:
            self.field = field
            super().__init__()

    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(id="field-description")
        self._render_display()

    def _render_display(self) -> None:
        if self.value:
            self.update(f"[bold]Description[/bold]\n{self.value}")
        else:
            self.update(f"[bold]Description[/bold]\n[dim italic]empty -- press enter to edit[/dim italic]")

    def key_enter(self) -> None:
        self.post_message(self.Activated(self))


class DetailScreen(ModalScreen):
    """Modal overlay showing full entity detail. Navigate with j/k, edit with enter."""

    BINDINGS = [
        Binding("escape", "back", "Close / stop editing"),
        Binding("j", "focus_next_field", "Down", show=False),
        Binding("k", "focus_prev_field", "Up", show=False),
        Binding("down", "focus_next_field", "Down", show=False),
        Binding("up", "focus_prev_field", "Up", show=False),
    ]

    DEFAULT_CSS = """
    DetailScreen {
        align: center middle;
    }

    #detail-container {
        width: 70;
        max-width: 90%;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    .detail-field {
        margin: 0 0 0 0;
    }

    .detail-separator {
        margin: 1 0 0 0;
    }

    #title-input {
        width: 100%;
        margin: 0 0 0 0;
    }

    #description-editor {
        height: auto;
        min-height: 5;
        max-height: 20;
        margin: 0 0 0 0;
    }
    """

    def __init__(self, entity: dict) -> None:
        self.entity = entity
        self._editing: str | None = None
        super().__init__()

    def compose(self) -> ComposeResult:
        e = self.entity
        color = MODULE_COLORS.get(e["module"], "white")

        with VerticalScroll(id="detail-container"):
            yield EditableField("Title", e["title"], "field-title")

            yield Static(f"[bold]ID:[/bold]       #{e['id']}", classes="detail-field")
            yield Static(f"[bold]Module:[/bold]   [{color}]{e['module']}[/{color}]", classes="detail-field")
            yield Static(f"[bold]Stage:[/bold]    {e['stage']}", classes="detail-field")

            if e.get("assignee"):
                yield Static(f"[bold]Assignee:[/bold] {e['assignee']}", classes="detail-field")

            contacts = json.loads(e.get("contacts") or "[]")
            if contacts:
                for c in contacts:
                    parts = [c["name"]]
                    if c.get("email"):
                        parts.append(c["email"])
                    if c.get("phone"):
                        parts.append(c["phone"])
                    yield Static(f"[bold]Contact:[/bold]  {' | '.join(parts)}", classes="detail-field")

            yield Static(f"[bold]Created:[/bold]  {e['created_at']}", classes="detail-field")
            yield Static(f"[bold]Updated:[/bold]  {e['updated_at']}", classes="detail-field")

            yield Static("", classes="detail-separator")
            yield DescriptionField(e.get("description") or "")

    def on_mount(self) -> None:
        self.query_one("#field-title", EditableField).focus()

    def _get_focusable_fields(self) -> list[EditableField | DescriptionField]:
        fields: list[EditableField | DescriptionField] = []
        fields.extend(self.query(EditableField))
        fields.extend(self.query(DescriptionField))
        return fields

    def action_focus_next_field(self) -> None:
        if self._editing:
            return
        fields = self._get_focusable_fields()
        if not fields:
            return
        focused = self.focused
        for i, f in enumerate(fields):
            if f is focused and i + 1 < len(fields):
                fields[i + 1].focus()
                return
        fields[0].focus()

    def action_focus_prev_field(self) -> None:
        if self._editing:
            return
        fields = self._get_focusable_fields()
        if not fields:
            return
        focused = self.focused
        for i, f in enumerate(fields):
            if f is focused and i - 1 >= 0:
                fields[i - 1].focus()
                return
        fields[-1].focus()

    def on_editable_field_activated(self, event: EditableField.Activated) -> None:
        if event.field.id == "field-title":
            self._editing = "title"
            field = event.field
            inp = Input(value=field.value, id="title-input")
            field.display = False
            self.query_one("#detail-container").mount(inp, before=field)
            inp.focus()

    def on_description_field_activated(self, event: DescriptionField.Activated) -> None:
        self._editing = "description"
        field = event.field
        editor = TextArea(
            field.value,
            id="description-editor",
            show_line_numbers=False,
        )
        field.display = False
        self.query_one("#detail-container").mount(editor, after=field)
        editor.focus()

    def action_back(self) -> None:
        if self._editing == "title":
            inp = self.query_one("#title-input", Input)
            new_value = inp.value
            inp.remove()
            field = self.query_one("#field-title", EditableField)
            field.value = new_value
            field._render_display()
            field.display = True
            field.focus()
            update_field(self.entity["id"], "title", new_value)
            self._editing = None
        elif self._editing == "description":
            editor = self.query_one("#description-editor", TextArea)
            new_value = editor.text
            editor.remove()
            field = self.query_one("#field-description", DescriptionField)
            field.value = new_value
            field._render_display()
            field.display = True
            field.focus()
            update_field(self.entity["id"], "description", new_value)
            self._editing = None
        else:
            self.dismiss()
