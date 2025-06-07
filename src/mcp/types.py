from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class TextContent:
    text: str
    type: str = "text"


@dataclass
class ImageContent:
    image_url: str
    type: str = "image_url"


@dataclass
class EmbeddedResource:
    type: str
    path: str
    resource: Any


Content = Union[TextContent, ImageContent, EmbeddedResource]


@dataclass
class CallToolResult:
    name: str
    success: bool
    content: List[Content]
    error: Optional[str] = None
    raw_output: Optional[Union[str, Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PromptMessage:
    role: str
    content: List[Content]


@dataclass
class Prompt:
    messages: List[PromptMessage]
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None


@dataclass
class GetPromptResult:
    prompt: Prompt
    prompt_id: str
    model_name: Optional[str] = None


@dataclass
class ReadResourceResult:
    path: str
    resource: Any


@dataclass
class Role:
    name: str
