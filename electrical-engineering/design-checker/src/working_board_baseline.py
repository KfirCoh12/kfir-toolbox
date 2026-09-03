"""Working-board baseline used while developing and stress-testing the tool."""
from __future__ import annotations

from .board_persistence import clear_last_board, load_last_board, save_last_board
from .sample_boards import office_700m2_150_people_board


def is_legacy_small_protection_test_board(payload: dict | None) -> bool:
    """Identify only the old two-branch MAIN-LV demo board.

    The migration is deliberately narrow so a user's own working board is never
    replaced merely because it happens to be small.
    """
    if not isinstance(payload, dict):
        return False
    if str(payload.get("board_id", "")).strip() != "MAIN-LV":
        return False
    if str(payload.get("description", "")).strip() != "Protection test board":
        return False
    branches = payload.get("branches")
    if not isinstance(branches, list) or len(branches) != 2:
        return False

    field = next((item for item in branches if isinstance(item, dict) and item.get("kind") == "field"), None)
    final = next((item for item in branches if isinstance(item, dict) and item.get("kind") == "final"), None)
    if field is None or final is None:
        return False
    return (
        str(field.get("feeder_id", "")).strip() == "F-01"
        and str(field.get("field_id", "")).strip() == "FIELD-01"
        and str(final.get("circuit_id", "")).strip() == "C-01"
        and str(final.get("parent_key", "")).strip() == str(field.get("uid", "")).strip()
    )


def ensure_office_working_baseline() -> tuple[dict, bool]:
    """Return the working board, seeding the office stress board when appropriate.

    A missing board or the exact legacy two-circuit demo is replaced by the reusable
    office fixture. Any other saved board is preserved unchanged.
    """
    saved = load_last_board()
    if saved is not None and not is_legacy_small_protection_test_board(saved):
        return saved, False

    fixture = office_700m2_150_people_board()
    if saved is not None:
        # This is an intentional replacement of the known demo board, not a partial
        # metadata update, so clear first rather than inheriting its project metadata.
        clear_last_board()
    save_last_board(fixture)
    return fixture, True
