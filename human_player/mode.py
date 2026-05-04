import enum

from arc_agi import OperationMode

from human_player.config import _load_user_config, _save_user_config


class PlayerMode(enum.Enum):
    """Player mode: HUMAN for local play, AGENT for AI-driven play."""

    HUMAN = "human"
    AGENT = "agent"


class AgentType(enum.Enum):
    """Built-in agent type identifiers used for scorecard tagging."""

    RANDOM = "random"
    LLM = "llm"
    FAST_LLM = "fastllm"
    REASONING_LLM = "reasoningllm"
    GUIDED_LLM = "guidedllm"
    CUSTOM = "custom"


def get_player_mode() -> PlayerMode:
    """Read the current player mode from user config."""
    cfg = _load_user_config()
    raw = cfg.get("player_mode", "human")
    try:
        return PlayerMode(raw)
    except ValueError:
        return PlayerMode.HUMAN


def set_player_mode(mode: PlayerMode) -> None:
    """Persist the player mode to user config."""
    cfg = _load_user_config()
    cfg["player_mode"] = mode.value
    _save_user_config(cfg)


def get_agent_type() -> AgentType | None:
    """Read the current agent type from user config, or None if unset."""
    cfg = _load_user_config()
    raw = cfg.get("agent_type")
    if raw is None:
        return None
    try:
        return AgentType(raw)
    except ValueError:
        return None


def set_agent_type(agent_type: AgentType | None) -> None:
    """Persist the agent type to user config. Pass None to clear."""
    cfg = _load_user_config()
    if agent_type is None:
        cfg.pop("agent_type", None)
    else:
        cfg["agent_type"] = agent_type.value
    _save_user_config(cfg)


def get_operation_mode() -> OperationMode:
    """Derive the ARC-AGI operation mode from player mode.

    HUMAN always maps to OFFLINE; AGENT maps to ONLINE.
    """
    mode = get_player_mode()
    if mode == PlayerMode.HUMAN:
        return OperationMode.OFFLINE
    return OperationMode.ONLINE


def get_player_tag() -> str:
    """Build a tag string for scorecard metadata.

    Returns "human" for human mode, or "agent:<type>" for agent mode.
    """
    mode = get_player_mode()
    if mode == PlayerMode.HUMAN:
        return "human"
    agent_type = get_agent_type()
    if agent_type is None:
        return "agent"
    return f"agent:{agent_type.value}"


def is_human_mode() -> bool:
    """Check if the current player mode is HUMAN."""
    return get_player_mode() == PlayerMode.HUMAN


def is_agent_mode() -> bool:
    """Check if the current player mode is AGENT."""
    return get_player_mode() == PlayerMode.AGENT
