"""
A derived client session for the MCP Agent framework.
It adds logging and supports sampling requests.
"""

from datetime import timedelta
from typing import TYPE_CHECKING

from aiohttp import ClientSession
from pydantic import FileUrl


# Stub class (ensure it's temporary only if you're waiting on implementation)
class ServerNotification:
    pass


from mcp.shared.session import (
    ProgressFnT,
    ReceiveResultT,
    RequestId,
    SendNotificationT,
    SendRequestT,
    SendResultT,
)

from mcp.types import (
    ErrorData,
    Implementation,
    ListRootsResult,
    Root,
    ToolListChangedNotification,
)

from mcp_agent.context_dependent import ContextDependent


class MCPAgentClientSession(ClientSession, ContextDependent):
    """
    Temporary stub for MCPAgentClientSession.
    Replace with real implementation as needed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
