"""
Agent implementation using the clean BaseAgent adapter.

This provides a streamlined implementation that adheres to AgentProtocol
while delegating LLM operations to an attached AugmentedLLMProtocol instance.
"""

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, TypeVar

from mcp_agent.agents.base_agent import BaseAgent
from mcp_agent.core.agent_types import AgentConfig
from mcp_agent.core.interactive_prompt import InteractivePrompt
from mcp_agent.human_input.types import HumanInputCallback
from mcp_agent.logger.logger import get_logger
from mcp_agent._mcp_local_backup.interfaces import AugmentedLLMProtocol

if TYPE_CHECKING:
    from mcp_agent.context import Context

logger = get_logger(__name__)

# Define a TypeVar for AugmentedLLM and its subclasses
LLM = TypeVar("LLM", bound=AugmentedLLMProtocol)


class Agent(BaseAgent):
    """
    An Agent is an entity that has access to a set of MCP servers and can interact with them.
    Each agent should have a purpose defined by its instruction.

    This implementation provides a clean adapter that adheres to AgentProtocol
    while delegating LLM operations to an attached AugmentedLLMProtocol instance.
    """

    def __init__(
        self,
        config: AgentConfig,  # Can be AgentConfig or backward compatible str name
        functions: Optional[List[Callable]] = None,
        connection_persistence: bool = True,
        human_input_callback: Optional[HumanInputCallback] = None,
        context: Optional["Context"] = None,
        **kwargs: Dict[str, Any],
    ) -> None:
        # Initialize with BaseAgent constructor
        super().__init__(
            config=config,
            functions=functions,
            connection_persistence=connection_persistence,
            human_input_callback=human_input_callback,
            context=context,
            **kwargs,
        )

    async def prompt(self, default_prompt: str = "", agent_name: Optional[str] = None) -> str:
        """
        Start an interactive prompt session with this agent.

        Args:
            default: Default message to use when user presses enter
            agent_name: Ignored for single agents, included for API compatibility

        Returns:
            The result of the interactive session
        """
        # Use the agent name as a string - ensure it's not the object itself
        agent_name_str = str(self.name)

        # Create agent_types dictionary with just this agent
        agent_types = {agent_name_str: self.agent_type.value}

        # Create the interactive prompt
        prompt = InteractivePrompt(agent_types=agent_types)

        # Define wrapper for send function
        async def send_wrapper(message, agent_name):
            return await self.send(message)

        # Start the prompt loop with just this agent
        return await prompt.prompt_loop(
            send_func=send_wrapper,
            default_agent=agent_name_str,
            available_agents=[agent_name_str],  # Only this agent
            prompt_provider=self,  # Pass self as the prompt provider since we implement the protocol
            default=default_prompt,
        )
