from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class CallToolResult:
    pass


@dataclass
class EmbeddedResource:
    pass


@dataclass
class GetPromptResult:
    pass


@dataclass
class ImageContent:
    pass


@dataclass
class Prompt:
    pass


@dataclass
class PromptMessage:
    pass


@dataclass
class ReadResourceResult:
    pass


@dataclass
class Role:
    pass


@dataclass
class TextContent:
    pass


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class ListToolsResult:
    tools: List[Tool]
