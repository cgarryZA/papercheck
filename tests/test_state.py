"""Tests for the audit state machine."""

from __future__ import annotations

import pytest

from papercheck.core.paths import state_file
from papercheck.core.state import AuditState, StateError


def _init(tmp_path) -> AuditState:
    return AuditState.init(
        tmp_path,
        run_id="2026-07-02T00:00:00Z",
        harness_version="0.1.0",
        git_commit=None,
    )


def test_init_creates_state(tmp_path) -> None:
    state = _init(tmp_path)
    assert state.stage == "INIT"
    assert state.completed_stages == ["INIT"]
    assert state_file(tmp_path).exists()
    assert len(state.stage_history) == 1


def test_advance_next_stage(tmp_path) -> None:
    state = _init(tmp_path)
    state.advance("SCANNED", at="t1")
    assert state.stage == "SCANNED"
    assert state.completed_stages == ["INIT", "SCANNED"]
    assert state.stage_history[-1]["stage"] == "SCANNED"


def test_skip_ahead_raises(tmp_path) -> None:
    state = _init(tmp_path)
    with pytest.raises(StateError):
        state.advance("SEGMENTED")


def test_backward_raises(tmp_path) -> None:
    state = _init(tmp_path)
    state.advance("SCANNED")
    with pytest.raises(StateError):
        state.advance("INIT")


def test_reentry_idempotent(tmp_path) -> None:
    state = _init(tmp_path)
    state.advance("SCANNED")
    state.advance("SCANNED")
    assert state.stage == "SCANNED"
    assert state.completed_stages == ["INIT", "SCANNED"]
    # History still records both entries.
    assert [h["stage"] for h in state.stage_history] == ["INIT", "SCANNED", "SCANNED"]


def test_load_round_trips(tmp_path) -> None:
    state = _init(tmp_path)
    state.advance("SCANNED")
    loaded = AuditState.load(tmp_path)
    assert loaded.stage == "SCANNED"
    assert loaded.completed_stages == ["INIT", "SCANNED"]
    assert loaded.run_id == state.run_id


def test_load_missing_raises(tmp_path) -> None:
    with pytest.raises(StateError):
        AuditState.load(tmp_path)


def test_require_at_least(tmp_path) -> None:
    state = _init(tmp_path)
    state.advance("SCANNED")
    # At/after should pass.
    state.require_at_least("INIT")
    state.require_at_least("SCANNED")
    # Before should raise.
    with pytest.raises(StateError):
        state.require_at_least("SEGMENTED")
