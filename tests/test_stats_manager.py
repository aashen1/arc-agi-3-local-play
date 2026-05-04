import json
import os
import tempfile

import pytest

from human_player.stats_manager import StatsManager


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sm(tmp_dir):
    return StatsManager(records_dir=tmp_dir)


class TestStatsManager:
    def test_record_and_get_best(self, sm):
        sm.record_attempt("ABCD", 0, 10, 5000, "WIN", "sess1")
        best = sm.get_best_record("ABCD", 0)
        assert best is not None
        assert best["steps"] == 10

    def test_best_record_none_when_no_wins(self, sm):
        sm.record_attempt("ABCD", 0, 10, 5000, "GAME_OVER", "sess1")
        assert sm.get_best_record("ABCD", 0) is None

    def test_best_steps_is_minimum(self, sm):
        sm.record_attempt("ABCD", 0, 10, 5000, "WIN", "sess1")
        sm.record_attempt("ABCD", 0, 5, 3000, "WIN", "sess2")
        best = sm.get_best_record("ABCD", 0)
        assert best["steps"] == 5

    def test_get_level_stats(self, sm):
        sm.record_attempt("ABCD", 0, 10, 5000, "WIN", "sess1")
        sm.record_attempt("ABCD", 0, 20, 8000, "GAME_OVER", "sess2")
        stats = sm.get_level_stats("ABCD", 0)
        assert stats["attempts"] == 2
        assert stats["wins"] == 1
        assert stats["best_steps"] == 10

    def test_get_game_summary(self, sm):
        sm.record_attempt("ABCD", 0, 10, 5000, "WIN", "sess1")
        sm.record_attempt("ABCD", 1, 8, 3000, "WIN", "sess2")
        summary = sm.get_game_summary("ABCD")
        assert summary["total_attempts"] == 2
        assert summary["total_wins"] == 2
        assert summary["levels_completed"] == 2
        assert summary["best_steps"] == 8

    def test_empty_stats(self, sm):
        stats = sm.get_level_stats("XXXX", 0)
        assert stats["attempts"] == 0
        assert stats["wins"] == 0

    def test_set_records_dir_clears_cache(self, sm, tmp_path):
        sm.record_attempt("ABCD", 0, 10, 5000, "WIN", "sess1")
        new_dir = str(tmp_path / "new_records")
        sm.set_records_dir(new_dir)
        assert sm._cache == {}
