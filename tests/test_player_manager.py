import json
import os
import tempfile

import pytest

from human_player.player_manager import PlayerManager


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def pm(tmp_dir, monkeypatch):
    monkeypatch.setattr("human_player.player_manager.PLAYERS_DIR", os.path.join(tmp_dir, "players"))
    monkeypatch.setattr("human_player.player_manager._load_user_config", lambda: {"current_player": "default"})
    monkeypatch.setattr("human_player.player_manager._save_user_config", lambda cfg: None)
    return PlayerManager()


class TestPlayerManager:
    def test_default_player(self, pm):
        assert pm.get_current_player() == "default"

    def test_set_player(self, pm):
        pm.set_player("alice")
        assert pm.get_current_player() == "alice"

    def test_set_player_trims_whitespace(self, pm):
        pm.set_player("  bob  ")
        assert pm.get_current_player() == "bob"

    def test_set_player_ignores_empty(self, pm):
        pm.set_player("   ")
        assert pm.get_current_player() == "default"

    def test_list_players_includes_default(self, pm):
        players = pm.list_players()
        assert "default" in players

    def test_get_player_data_dir(self, pm):
        path = pm.get_player_data_dir("testplayer")
        assert os.path.isdir(path)

    def test_get_recordings_dir(self, pm):
        path = pm.get_recordings_dir("ABCD", "testplayer")
        assert os.path.isdir(path)
        assert "ABCD" in path

    def test_delete_player(self, pm):
        pm.get_player_data_dir("todelete")
        assert pm.delete_player("todelete") is True

    def test_cannot_delete_current_player(self, pm):
        assert pm.delete_player("default") is False

    def test_delete_nonexistent_player(self, pm):
        assert pm.delete_player("nonexistent") is False

    def test_get_player_metadata_empty(self, pm):
        meta = pm.get_player_metadata("newplayer")
        assert meta["total_levels_completed"] == 0
        assert meta["total_games_played"] == 0
