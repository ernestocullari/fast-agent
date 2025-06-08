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
