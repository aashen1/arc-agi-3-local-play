from abc import ABC, abstractmethod

from arcengine import GameAction

from human_player.mode import AgentType


class AgentBase(ABC):
    agent_type: AgentType = AgentType.CUSTOM

    @abstractmethod
    def is_done(self, frames: list, latest_frame) -> bool:
        raise NotImplementedError

    @abstractmethod
    def choose_action(self, frames: list, latest_frame) -> GameAction:
        raise NotImplementedError

    def get_reasoning(self) -> dict | str | None:
        return None
