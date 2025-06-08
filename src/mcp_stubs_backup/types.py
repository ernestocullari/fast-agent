from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union


class SamplingMessage(BaseModel):
    role: str
    content: str


class CallToolResult(BaseModel):
    tool_name: str
    output: Any


class EmbeddedResource(BaseModel):
    url: str
    content_type: Optional[str] = None


class GetPromptResult(BaseModel):
    prompt_id: str
    content: str


class ImageContent(BaseModel):
    url: str
    alt_text: Optional[str] = None


class Prompt(BaseModel):
    id: str
    content: str


class PromptMessage(BaseModel):
    role: str
    content: Union[str, Dict[str, Any]]


class ReadResourceResult(BaseModel):
    resource_id: str
    data: Dict[str, Any]


class Role(BaseModel):
    name: str
    permissions: List[str]


class TextContent(BaseModel):
    text: str


class Tool(BaseModel):
    name: str
    description: Optional[str] = None


class ListToolsResult(BaseModel):
    tools: List[Tool]


class CreateMessageRequestParams(BaseModel):
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    additional_inputs: Optional[Dict[str, Any]] = None


class BlobResourceContents(BaseModel):
    id: str
    data: Union[str, bytes]
    content_type: Optional[str] = None


class TextResourceContents(BaseModel):
    id: str
    text: str
    content_type: Optional[str] = None


class Annotations(BaseModel):
    start: int
    end: int
    label: str
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ResourceContents(BaseModel):
    blob: Optional[BlobResourceContents] = None
    text: Optional[TextResourceContents] = None


class ErrorData(BaseModel):
    message: str
    code: Optional[int] = None


class Implementation(BaseModel):
    name: str


class ListRootsResult(BaseModel):
    roots: List[str]


class Root(BaseModel):
    id: str
    name: str


class ToolListChangedNotification(BaseModel):
    tool_name: str
    change_type: str


class CreateMessageResult(BaseModel):
    message_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


# src/mcp/types.py

# === Placeholder types for MCP protocol ===


class JSONRPCMessage:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Stub: JSONRPCMessage")


class ServerCapabilities:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Stub: ServerCapabilities")
