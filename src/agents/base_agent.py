"""
Base Agent Class
Foundation for all ADK agents with A2A communication support
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import logging
import asyncio
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all ADK agents

    Note: This is a simplified ADK-compatible agent implementation.
    In production, this would inherit from the actual ADK Agent class.
    """

    def __init__(
        self,
        name: str,
        description: str,
        llm_provider=None,
        storage_backend=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base agent

        Args:
            name: Agent name
            description: Agent description
            llm_provider: LLM provider instance
            storage_backend: Storage backend instance
            config: Additional configuration
        """
        self.name = name
        self.description = description
        self.llm_provider = llm_provider
        self.storage_backend = storage_backend
        self.config = config or {}

        # A2A communication registry
        self._agent_registry: Dict[str, 'BaseAgent'] = {}

        logger.info(f"Initialized agent: {name}")

    def register_agent(self, agent_name: str, agent: 'BaseAgent') -> None:
        """
        Register another agent for A2A communication

        Args:
            agent_name: Name of the agent to register
            agent: Agent instance
        """
        self._agent_registry[agent_name] = agent
        logger.debug(f"{self.name}: Registered agent '{agent_name}'")

    async def call_agent(
        self,
        agent: str,
        action: str,
        params: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call another agent (A2A communication)

        This is the core A2A method that enables agent-to-agent communication.

        Args:
            agent: Target agent name
            action: Action to invoke on the agent
            params: Parameters for the action
            correlation_id: Optional correlation ID for request tracking

        Returns:
            Response from the target agent

        Raises:
            ValueError: If agent not found or action not available
        """
        if agent not in self._agent_registry:
            raise ValueError(f"Agent '{agent}' not registered")

        target_agent = self._agent_registry[agent]

        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = f"{self.name}_{agent}_{datetime.utcnow().isoformat()}"

        # Create A2A message
        message = {
            "sender": self.name,
            "recipient": agent,
            "action": action,
            "params": params,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"A2A Call: {self.name} -> {agent}.{action}() [correlationId={correlation_id}]")
        logger.debug(f"A2A Message: {json.dumps(message, indent=2)}")

        try:
            # Invoke action on target agent
            if not hasattr(target_agent, action):
                raise ValueError(f"Agent '{agent}' does not have action '{action}'")

            action_method = getattr(target_agent, action)
            result = await action_method(**params)

            logger.info(f"A2A Response: {agent}.{action}() -> {self.name} [correlationId={correlation_id}]")

            return {
                "success": True,
                "data": result,
                "correlation_id": correlation_id,
                "error": None
            }

        except Exception as e:
            logger.error(f"A2A Call failed: {self.name} -> {agent}.{action}(): {e}")
            return {
                "success": False,
                "data": None,
                "correlation_id": correlation_id,
                "error": str(e)
            }

    async def send_message(
        self,
        recipient: str,
        content: str,
        message_type: str = "info"
    ) -> None:
        """
        Send a message to another agent (fire-and-forget)

        Args:
            recipient: Target agent name
            content: Message content
            message_type: Message type (info, warning, error)
        """
        logger.info(f"Message: {self.name} -> {recipient}: {content}")

    @abstractmethod
    async def process(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main processing method (to be implemented by each agent)

        Returns:
            Processing result
        """
        pass

    def get_capabilities(self) -> List[str]:
        """
        Get list of agent capabilities (actions)

        Returns:
            List of available action names
        """
        capabilities = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and not attr_name.startswith("_") and attr_name not in ["register_agent", "call_agent", "send_message", "get_capabilities", "process"]:
                capabilities.append(attr_name)
        return capabilities

    def get_info(self) -> Dict[str, Any]:
        """
        Get agent information

        Returns:
            Dictionary with agent metadata
        """
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.get_capabilities(),
            "registered_agents": list(self._agent_registry.keys())
        }
