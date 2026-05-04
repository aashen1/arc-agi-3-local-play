import pytest

from human_player.config import _load_user_config, _save_user_config
from human_player.mode import (
    AgentType,
    PlayerMode,
    get_agent_type,
    get_player_mode,
    get_player_tag,
    is_agent_mode,
    is_human_mode,
    set_agent_type,
    set_player_mode,
)


@pytest.fixture(autouse=True)
def clean_config(tmp_path, monkeypatch):
    cfg_file = str(tmp_path / "user_config.json")
    monkeypatch.setattr("human_player.config.USER_CONFIG_FILE", cfg_file)
    monkeypatch.setattr("human_player.mode._load_user_config", _load_user_config)
    monkeypatch.setattr("human_player.mode._save_user_config", _save_user_config)


class TestPlayerMode:
    def test_default_is_human(self):
        assert get_player_mode() == PlayerMode.HUMAN

    def test_set_and_get(self):
        set_player_mode(PlayerMode.AGENT)
        assert get_player_mode() == PlayerMode.AGENT
        set_player_mode(PlayerMode.HUMAN)
        assert get_player_mode() == PlayerMode.HUMAN

    def test_is_human_mode(self):
        assert is_human_mode() is True
        set_player_mode(PlayerMode.AGENT)
        assert is_human_mode() is False

    def test_is_agent_mode(self):
        assert is_agent_mode() is False
        set_player_mode(PlayerMode.AGENT)
        assert is_agent_mode() is True


class TestAgentType:
    def test_default_is_none(self):
        assert get_agent_type() is None

    def test_set_and_get(self):
        set_agent_type(AgentType.LLM)
        assert get_agent_type() == AgentType.LLM
        set_agent_type(None)
        assert get_agent_type() is None


class TestPlayerTag:
    def test_human_tag(self):
        set_player_mode(PlayerMode.HUMAN)
        assert get_player_tag() == "human"

    def test_agent_tag(self):
        set_player_mode(PlayerMode.AGENT)
        set_agent_type(AgentType.LLM)
        assert get_player_tag() == "agent:llm"

    def test_agent_no_type(self):
        set_player_mode(PlayerMode.AGENT)
        set_agent_type(None)
        assert get_player_tag() == "agent"
