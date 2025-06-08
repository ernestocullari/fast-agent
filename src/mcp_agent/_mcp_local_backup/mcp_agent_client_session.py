"""
A derived client session for the MCP Agent framework.
It adds logging and supports sampling requests.
"""

from datetime import timedelta
from typing import TYPE_CHECKING

from aiohttp import ClientSession


# Temporary or local stub class (if not already defined)
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
from mcp.types import ErrorData, Implementation, ListRootsResult, Root, ToolListChangedNotification
from pydantic import FileUrl

from mcp_agent.context_dependent import ContextDependent
from mcp_agent.logger.logger import get_logger
from mcp_agent._mcp_local_backup.helpers.server_config_helpers import get_server_config
from mcp_agent._mcp_local_backup.sampling import sample
