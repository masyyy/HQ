from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.binding import Binding
from textual.reactive import reactive

from hq.tui.banner import get_banner
from hq.tui.kanban import KanbanBoard, Card, KanbanColumn
from hq.tui.detail import DetailScreen
from hq.config import get_stages
from hq.db.queries import move_entity_by_id


MODULES = ["board", "crm"]

# Keys that move mode intercepts
_MOVE_LEFT_KEYS = {"h", "left"}
_MOVE_RIGHT_KEYS = {"l", "right"}
_MOVE_EXIT_KEYS = {"escape", "m", "enter", "q"}


class ModuleBar(Static):
    """Simple tab bar showing which module is active."""

    DEFAULT_CSS = """
    ModuleBar {
        height: 1;
        width: 100%;
        background: $primary-background;
        padding: 0 1;
    }
    """

    def render_bar(self, active: str, move_mode: bool = False) -> None:
        parts = []
        for i, mod in enumerate(MODULES):
            key = str(i + 1)
            if mod == active:
                parts.append(f"[bold reverse] {key}:{mod.upper()} [/bold reverse]")
            else:
                parts.append(f"[dim] {key}:{mod.upper()} [/dim]")
        bar = "  ".join(parts)
        if move_mode:
            bar += "    [bold yellow]MOVE[/bold yellow] [dim]h/l: move, esc: done[/dim]"
        self.update(bar)


class HQApp(App):
    """HQ Company OS - TUI"""

    TITLE = "HQ"
    AUTO_FOCUS = None

    active_module: reactive[str] = reactive("board")
    _move_mode: bool = False
    _move_entity_id: int | None = None

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("1", "show_module('board')", "Board", show=False),
        Binding("2", "show_module('crm')", "CRM", show=False),
        Binding("bracketright", "next_module", "Next", show=False),
        Binding("bracketleft", "prev_module", "Prev", show=False),
        Binding("j", "focus_next_card", "Down", show=False),
        Binding("k", "focus_prev_card", "Up", show=False),
        Binding("h", "focus_prev_column", "Left", show=False),
        Binding("l", "focus_next_column", "Right", show=False),
        Binding("up", "focus_prev_card", "Up", show=False),
        Binding("down", "focus_next_card", "Down", show=False),
        Binding("left", "focus_prev_column", "Left", show=False),
        Binding("right", "focus_next_column", "Right", show=False),
        Binding("m", "start_move", "Move"),
        Binding("question_mark", "help", "Help"),
    ]

    DEFAULT_CSS = """
    #banner {
        text-align: center;
        color: $accent;
        height: auto;
        padding: 1 0 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(get_banner(), id="banner")
        yield ModuleBar()
        for mod in MODULES:
            yield KanbanBoard(mod, id=f"board-{mod}")
        yield Footer()

    # -- Key event routing --
    # When in move mode, we intercept keys before Textual's binding system.
    # This avoids needing a separate screen and keeps focus on the card.

    def on_key(self, event: events.Key) -> None:
        if not self._move_mode:
            return
        key = event.key
        if key in _MOVE_LEFT_KEYS:
            self._move_card(-1)
            event.prevent_default()
            event.stop()
        elif key in _MOVE_RIGHT_KEYS:
            self._move_card(+1)
            event.prevent_default()
            event.stop()
        elif key in _MOVE_EXIT_KEYS:
            self._exit_move_mode()
            event.prevent_default()
            event.stop()
        else:
            # Block all other keys during move mode
            event.prevent_default()
            event.stop()

    # -- Lifecycle --

    def on_mount(self) -> None:
        self._update_banner_for_viewport()
        self._sync_visible_board()

    def on_resize(self, event: events.Resize) -> None:
        self._update_banner_for_viewport()

    def _update_banner_for_viewport(self) -> None:
        banner = self.query_one("#banner", Static)
        h, w = self.size.height, self.size.width
        if h < 22 or w < 56:
            banner.display = False
            return
        banner.display = True
        banner.update(get_banner(compact=h < 30 or w < 76))

    def _sync_visible_board(self) -> None:
        for mod in MODULES:
            board = self.query_one(f"#board-{mod}", KanbanBoard)
            is_active = mod == self.active_module
            board.display = is_active
            if is_active:
                board.refresh_board()
        self.query_one(ModuleBar).render_bar(self.active_module, self._move_mode)

    def watch_active_module(self, value: str) -> None:
        self._sync_visible_board()

    # -- Card navigation helpers --

    def _get_visible_cards(self) -> list[Card]:
        return list(self.query_one(f"#board-{self.active_module}", KanbanBoard).query(Card))

    def _cards_in_column(self, card: Card) -> list[Card]:
        column = card.parent
        if column is None:
            return [card]
        return list(column.query(Card))

    def _sibling_column_card(self, card: Card, direction: int) -> Card | None:
        column = card.parent
        if column is None or column.parent is None:
            return None
        columns = list(column.parent.query(KanbanColumn))
        try:
            col_idx = columns.index(column)
        except ValueError:
            return None
        new_idx = col_idx + direction
        while 0 <= new_idx < len(columns):
            col_cards = list(columns[new_idx].query(Card))
            if col_cards:
                return col_cards[0]
            new_idx += direction
        return None

    def _focus_card_by_id(self, entity_id: int) -> None:
        """Find a card by entity ID and focus it."""
        board = self.query_one(f"#board-{self.active_module}", KanbanBoard)
        for card in board.query(Card):
            if card.entity["id"] == entity_id:
                card.focus()
                return

    # -- Move mode --

    def action_start_move(self) -> None:
        focused = self.focused
        if not isinstance(focused, Card):
            return
        self._move_mode = True
        self._move_entity_id = focused.entity["id"]
        self.query_one(ModuleBar).render_bar(self.active_module, True)

    def _exit_move_mode(self) -> None:
        entity_id = self._move_entity_id
        self._move_mode = False
        self._move_entity_id = None
        self.query_one(ModuleBar).render_bar(self.active_module, False)
        if entity_id is not None:
            self._focus_card_by_id(entity_id)

    def _move_card(self, direction: int) -> None:
        if self._move_entity_id is None:
            return
        # Find the current card to get its stage
        board = self.query_one(f"#board-{self.active_module}", KanbanBoard)
        current_card = None
        for card in board.query(Card):
            if card.entity["id"] == self._move_entity_id:
                current_card = card
                break
        if current_card is None:
            return

        stages = get_stages(self.active_module)
        current_stage = current_card.entity["stage"]
        try:
            idx = stages.index(current_stage)
        except ValueError:
            return
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(stages):
            return

        new_stage = stages[new_idx]
        move_entity_by_id(self._move_entity_id, new_stage)
        board.refresh_board()
        self._focus_card_by_id(self._move_entity_id)

    # -- Navigation actions --

    def action_focus_next_card(self) -> None:
        cards = self._get_visible_cards()
        if not cards:
            return
        focused = self.focused
        if not isinstance(focused, Card):
            cards[0].focus()
            return
        col_cards = self._cards_in_column(focused)
        try:
            idx = col_cards.index(focused)
        except ValueError:
            return
        if idx + 1 < len(col_cards):
            col_cards[idx + 1].focus()

    def action_focus_prev_card(self) -> None:
        cards = self._get_visible_cards()
        if not cards:
            return
        focused = self.focused
        if not isinstance(focused, Card):
            cards[0].focus()
            return
        col_cards = self._cards_in_column(focused)
        try:
            idx = col_cards.index(focused)
        except ValueError:
            return
        if idx - 1 >= 0:
            col_cards[idx - 1].focus()

    def action_focus_next_column(self) -> None:
        focused = self.focused
        if not isinstance(focused, Card):
            cards = self._get_visible_cards()
            if cards:
                cards[0].focus()
            return
        target = self._sibling_column_card(focused, +1)
        if target:
            target.focus()

    def action_focus_prev_column(self) -> None:
        focused = self.focused
        if not isinstance(focused, Card):
            cards = self._get_visible_cards()
            if cards:
                cards[0].focus()
            return
        target = self._sibling_column_card(focused, -1)
        if target:
            target.focus()

    # -- Screen pushes --

    def on_card_selected(self, event: Card.Selected) -> None:
        self.push_screen(DetailScreen(event.entity), callback=self._on_detail_dismissed)

    def _on_detail_dismissed(self, result: object) -> None:
        board = self.query_one(f"#board-{self.active_module}", KanbanBoard)
        board.refresh_board()

    # -- Module switching --

    def action_show_module(self, module: str) -> None:
        self.active_module = module

    def action_next_module(self) -> None:
        idx = MODULES.index(self.active_module)
        self.active_module = MODULES[(idx + 1) % len(MODULES)]

    def action_prev_module(self) -> None:
        idx = MODULES.index(self.active_module)
        self.active_module = MODULES[(idx - 1) % len(MODULES)]

    # -- Misc --

    def action_refresh(self) -> None:
        for board in self.query(KanbanBoard):
            board.refresh_board()

    def action_help(self) -> None:
        self.notify(
            "1/2 [/]: module | j/k/h/l: navigate | enter: detail | m: move | r: refresh | q: quit",
            title="Help",
        )
