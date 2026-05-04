import pytest

from human_player.config import (
    get_keymap_scheme, set_keymap_scheme,
    get_view_mode, set_view_mode,
    get_sync_mode, set_sync_mode,
    SYNC_MODE_CONSERVATIVE, SYNC_MODE_AUTO,
    KEYMAP_WASD, KEYMAP_ARROWS,
    _load_user_config, _save_user_config,
)


@pytest.fixture(autouse=True)
def clean_config(tmp_path, monkeypatch):
    cfg_file = str(tmp_path / "user_config.json")
    monkeypatch.setattr("human_player.config.USER_CONFIG_FILE", cfg_file)


class TestKeymapScheme:
    def test_default_is_wasd(self):
        assert get_keymap_scheme() == "wasd"

    def test_set_arrows(self):
        set_keymap_scheme("arrows")
        assert get_keymap_scheme() == "arrows"

    def test_set_wasd(self):
        set_keymap_scheme("arrows")
        set_keymap_scheme("wasd")
        assert get_keymap_scheme() == "wasd"


class TestViewMode:
    def test_default_is_grid(self):
        assert get_view_mode() == "grid"

    def test_set_list(self):
        set_view_mode("list")
        assert get_view_mode() == "list"


class TestSyncMode:
    def test_default_is_conservative(self):
        assert get_sync_mode() == SYNC_MODE_CONSERVATIVE

    def test_set_auto(self):
        set_sync_mode(SYNC_MODE_AUTO)
        assert get_sync_mode() == SYNC_MODE_AUTO

    def test_invalid_value_defaults_to_conservative(self):
        set_sync_mode("invalid")
        assert get_sync_mode() == SYNC_MODE_CONSERVATIVE
