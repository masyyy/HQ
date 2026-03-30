"""Tests for ticket ordering (position) within columns."""

import pytest

from hq.db.models import get_db
from hq.db.queries import (
    add_entity,
    list_entities,
    move_entity,
    move_entity_by_id,
    reorder_entity,
    reorder_entity_by_id,
    delete_entity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _titles(module="board", stage=None):
    """Return ordered list of titles for a module (optionally filtered by stage)."""
    return [e["title"] for e in list_entities(module, stage=stage)]


def _positions(module="board", stage=None):
    """Return ordered list of (title, position) tuples."""
    return [(e["title"], e["position"]) for e in list_entities(module, stage=stage)]


def _add_board_items(*titles, stage=None):
    """Add multiple board items, return list of created entities."""
    return [add_entity("board", t, stage=stage) for t in titles]


# ---------------------------------------------------------------------------
# Position assignment on creation
# ---------------------------------------------------------------------------

class TestPositionOnCreate:
    def test_sequential_positions(self):
        items = _add_board_items("A", "B", "C")
        assert [(i["title"], i["position"]) for i in items] == [
            ("A", 0), ("B", 1), ("C", 2),
        ]

    def test_list_respects_position_order(self):
        _add_board_items("A", "B", "C")
        assert _titles(stage="backlog") == ["A", "B", "C"]

    def test_different_stages_have_independent_positions(self):
        add_entity("board", "Backlog-1")
        add_entity("board", "Todo-1", stage="todo")
        add_entity("board", "Backlog-2")
        assert _positions(stage="backlog") == [("Backlog-1", 0), ("Backlog-2", 1)]
        assert _positions(stage="todo") == [("Todo-1", 0)]


# ---------------------------------------------------------------------------
# Reorder within column
# ---------------------------------------------------------------------------

class TestReorderWithinColumn:
    def test_move_down(self):
        _add_board_items("A", "B", "C")
        reorder_entity("board", "A", "down")
        assert _titles(stage="backlog") == ["B", "A", "C"]

    def test_move_up(self):
        _add_board_items("A", "B", "C")
        reorder_entity("board", "C", "up")
        assert _titles(stage="backlog") == ["A", "C", "B"]

    def test_move_to_top(self):
        _add_board_items("A", "B", "C")
        reorder_entity("board", "C", "top")
        assert _positions(stage="backlog") == [("C", 0), ("A", 1), ("B", 2)]

    def test_move_to_bottom(self):
        _add_board_items("A", "B", "C")
        reorder_entity("board", "A", "bottom")
        assert _positions(stage="backlog") == [("B", 0), ("C", 1), ("A", 2)]

    def test_boundary_reorder_is_noop(self):
        """up at top, down at bottom, top when already top, bottom when already bottom."""
        _add_board_items("A", "B")
        reorder_entity("board", "A", "up")
        reorder_entity("board", "A", "top")
        reorder_entity("board", "B", "down")
        reorder_entity("board", "B", "bottom")
        assert _positions(stage="backlog") == [("A", 0), ("B", 1)]

    def test_multiple_reorders(self):
        _add_board_items("A", "B", "C", "D")
        reorder_entity("board", "D", "top")
        reorder_entity("board", "A", "down")
        # after top: D A B C  ->  after down A: D B A C
        assert _titles(stage="backlog") == ["D", "B", "A", "C"]

    def test_invalid_direction_raises(self):
        _add_board_items("A")
        with pytest.raises(ValueError, match="Invalid direction"):
            reorder_entity("board", "A", "sideways")

    def test_reorder_by_id(self):
        items = _add_board_items("A", "B", "C")
        reorder_entity_by_id(items[2]["id"], "top")
        assert _titles(stage="backlog") == ["C", "A", "B"]


# ---------------------------------------------------------------------------
# Reorder doesn't affect other stages
# ---------------------------------------------------------------------------

class TestReorderIsolation:
    def test_reorder_does_not_affect_other_stage(self):
        _add_board_items("Back-1", "Back-2")
        add_entity("board", "Todo-1", stage="todo")
        add_entity("board", "Todo-2", stage="todo")

        reorder_entity("board", "Back-2", "up")

        assert _titles(stage="backlog") == ["Back-2", "Back-1"]
        assert _titles(stage="todo") == ["Todo-1", "Todo-2"]


# ---------------------------------------------------------------------------
# Position after moving between stages
# ---------------------------------------------------------------------------

class TestPositionOnStageMove:
    def test_move_to_new_stage_appends(self):
        _add_board_items("A", "B", "C")
        add_entity("board", "Todo-1", stage="todo")

        entity = move_entity("board", "B", "todo")
        assert entity["position"] == 1

        assert _titles(stage="todo") == ["Todo-1", "B"]
        assert _titles(stage="backlog") == ["A", "C"]

    def test_move_by_id_to_new_stage(self):
        items = _add_board_items("A", "B", "C")
        move_entity_by_id(items[1]["id"], "todo")

        assert _titles(stage="todo") == ["B"]
        assert _titles(stage="backlog") == ["A", "C"]

    def test_move_to_empty_stage_gets_position_zero(self):
        _add_board_items("A")
        entity = move_entity("board", "A", "todo")
        assert entity["position"] == 0

    def test_reorder_after_stage_move(self):
        _add_board_items("A", "B", "C")
        move_entity("board", "A", "todo")
        move_entity("board", "B", "todo")
        move_entity("board", "C", "todo")

        reorder_entity("board", "C", "top")
        assert _titles(stage="todo") == ["C", "A", "B"]


# ---------------------------------------------------------------------------
# Position after delete
# ---------------------------------------------------------------------------

class TestPositionAfterDelete:
    def test_reorder_after_delete(self):
        _add_board_items("A", "B", "C")
        delete_entity("board", "B")
        assert _titles(stage="backlog") == ["A", "C"]

        reorder_entity("board", "C", "up")
        assert _titles(stage="backlog") == ["C", "A"]


# ---------------------------------------------------------------------------
# Single-item edge case
# ---------------------------------------------------------------------------

class TestSingleItem:
    def test_reorder_single_item_is_noop(self):
        _add_board_items("A")
        for direction in ("up", "down", "top", "bottom"):
            reorder_entity("board", "A", direction)
        assert _positions(stage="backlog") == [("A", 0)]


# ---------------------------------------------------------------------------
# Same-stage move is a no-op
# ---------------------------------------------------------------------------

class TestSameStageMove:
    def test_move_to_same_stage_preserves_position(self):
        _add_board_items("A", "B", "C")
        reorder_entity("board", "A", "bottom")
        move_entity("board", "A", "backlog")
        assert _titles(stage="backlog") == ["B", "C", "A"]

    def test_move_by_id_to_same_stage_preserves_position(self):
        items = _add_board_items("A", "B", "C")
        move_entity_by_id(items[0]["id"], "backlog")
        assert _titles(stage="backlog") == ["A", "B", "C"]

    def test_move_to_same_stage_does_not_update_timestamp(self):
        items = _add_board_items("A")
        db = get_db()
        original = db.execute(
            "SELECT updated_at FROM entities WHERE id = ?", [items[0]["id"]]
        ).fetchone()[0]

        move_entity("board", "A", "backlog")

        after = db.execute(
            "SELECT updated_at FROM entities WHERE id = ?", [items[0]["id"]]
        ).fetchone()[0]
        assert original == after


# ---------------------------------------------------------------------------
# Reorder only updates moved entity's timestamp
# ---------------------------------------------------------------------------

class TestReorderTimestamps:
    def test_reorder_preserves_sibling_timestamps(self):
        items = _add_board_items("A", "B", "C")
        db = get_db()

        def _ts(entity_id):
            return db.execute(
                "SELECT updated_at FROM entities WHERE id = ?", [entity_id]
            ).fetchone()[0]

        ts_a = _ts(items[0]["id"])
        ts_b = _ts(items[1]["id"])
        ts_c = _ts(items[2]["id"])

        reorder_entity("board", "C", "top")

        assert _ts(items[0]["id"]) == ts_a
        assert _ts(items[1]["id"]) == ts_b
        assert _ts(items[2]["id"]) != ts_c
