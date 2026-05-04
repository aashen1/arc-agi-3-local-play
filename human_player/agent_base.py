from abc import ABC, abstractmethod

from arcengine import GameAction

from human_player.mode import AgentType


class AgentBase(ABC):
    """Abstract base class for AI agents that play ARC-AGI-3 games.

    Subclass this to create a custom agent. Only two methods are required:
    ``is_done`` and ``choose_action``. Optionally override ``get_reasoning``
    to provide explainability data for recording.
    """

    agent_type: AgentType = AgentType.CUSTOM

    @abstractmethod
    def is_done(self, frames: list, latest_frame) -> bool:
        """Return True when the agent decides to stop playing.

        Args:
            frames: All observed frames so far.
            latest_frame: The most recent frame observation.

        Returns:
            True if the agent wants to end the session, False to continue.
        """
        raise NotImplementedError

    @abstractmethod
    def choose_action(self, frames: list, latest_frame) -> GameAction:
        """Select the next action given the current game state.

        Args:
            frames: All observed frames so far.
            latest_frame: The most recent frame observation.

        Returns:
            The GameAction to execute.
        """
        raise NotImplementedError

    def get_reasoning(self) -> dict | str | None:
        """Return an optional reasoning trace for the last action.

        Override this to provide explainability data that will be included
        in the official recording when running in agent mode.

        Returns:
            A dict, string, or None describing the agent's reasoning.
        """
        return None
