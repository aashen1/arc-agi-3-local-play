import json
import os
import tempfile

import pytest

from human_player.level_manager import LevelManager


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def lm(tmp_dir):
    progress_file = os.path.join(tmp_dir, "progress.json")
    return LevelManager(progress_file=progress_file)


class TestLevelManager:
    def test_initial_progress_is_empty(self, lm):
        assert lm.progress["games"] == {}

    def test_update_level_status(self, lm):
        lm.update_level_status("ABCD", 0, 10, 5000)
        info = lm.get_level_info("ABCD", 0)
        assert info["completed"] is True
        assert info["best_steps"] == 10
        assert info["best_time_ms"] == 5000

    def test_best_steps_kept_on_worse(self, lm):
        lm.update_level_status("ABCD", 0, 10, 5000)
        lm.update_level_status("ABCD", 0, 20, 3000)
        info = lm.get_level_info("ABCD", 0)
        assert info["best_steps"] == 10
        assert info["best_time_ms"] == 3000

    def test_get_completed_count(self, lm):
        lm.update_level_status("ABCD", 0, 5, 1000)
        lm.update_level_status("ABCD", 1, 8, 2000)
        assert lm.get_completed_count("ABCD") == 2

    def test_get_next_uncompleted_level(self, lm):
        assert lm.get_next_uncompleted_level("ABCD") == 0
        lm.update_level_status("ABCD", 0, 5, 1000)
        lm.update_total_levels("ABCD", 5)
        assert lm.get_next_uncompleted_level("ABCD") == 1

    def test_is_fully_completed(self, lm):
        lm.update_total_levels("ABCD", 2)
        assert lm.is_fully_completed("ABCD") is False
        lm.update_level_status("ABCD", 0, 5, 1000)
        lm.update_level_status("ABCD", 1, 8, 2000)
        assert lm.is_fully_completed("ABCD") is True

    def test_persistence(self, tmp_dir):
        progress_file = os.path.join(tmp_dir, "progress.json")
        lm1 = LevelManager(progress_file=progress_file)
        lm1.update_level_status("ABCD", 0, 5, 1000)
        lm2 = LevelManager(progress_file=progress_file)
        assert lm2.get_level_info("ABCD", 0)["completed"] is True

    def test_corrupted_file_returns_default(self, tmp_dir):
        progress_file = os.path.join(tmp_dir, "progress.json")
        with open(progress_file, "w") as f:
            f.write("{invalid json")
        lm = LevelManager(progress_file=progress_file)
        assert lm.progress["games"] == {}

    def test_get_last_played_game_id(self, lm):
        assert lm.get_last_played_game_id() is None
        lm.update_level_status("ABCD", 0, 5, 1000)
        lm.update_level_status("EFGH", 0, 5, 1000)
        assert lm.get_last_played_game_id() == "EFGH"
