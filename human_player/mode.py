import enum

from arc_agi import OperationMode

from human_player.config import _load_user_config, _save_user_config


class PlayerMode(enum.Enum):
    HUMAN = "human"
    AGENT = "agent"


class AgentType(enum.Enum):
    RANDOM = "random"
    LLM = "llm"
    FAST_LLM = "fastllm"
    REASONING_LLM = "reasoningllm"
    GUIDED_LLM = "guidedllm"
    CUSTOM = "custom"


def get_player_mode() -> PlayerMode:
    cfg = _load_user_config()
    raw = cfg.get("player_mode", "human")
    try:
        return PlayerMode(raw)
    except ValueError:
        return PlayerMode.HUMAN


def set_player_mode(mode: PlayerMode) -> None:
    cfg = _load_user_config()
    cfg["player_mode"] = mode.value
    _save_user_config(cfg)


def get_agent_type() -> AgentType | None:
    cfg = _load_user_config()
    raw = cfg.get("agent_type")
    if raw is None:
        return None
    try:
        return AgentType(raw)
    except ValueError:
        return None


def set_agent_type(agent_type: AgentType | None) -> None:
    cfg = _load_user_config()
    if agent_type is None:
        cfg.pop("agent_type", None)
    else:
        cfg["agent_type"] = agent_type.value
    _save_user_config(cfg)


def get_operation_mode() -> OperationMode:
    mode = get_player_mode()
    if mode == PlayerMode.HUMAN:
        return OperationMode.NORMAL
    return OperationMode.ONLINE


def get_player_tag() -> str:
    mode = get_player_mode()
    if mode == PlayerMode.HUMAN:
        return "human"
    agent_type = get_agent_type()
    if agent_type is None:
        return "agent"
    return f"agent:{agent_type.value}"


def is_human_mode() -> bool:
    return get_player_mode() == PlayerMode.HUMAN


def is_agent_mode() -> bool:
    return get_player_mode() == PlayerMode.AGENT
