from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class SamplingMessage(BaseModel):
    role: str
    content: str


class CreateMessageRequestParams(BaseModel):
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    additional_inputs: Optional[Dict[str, Any]] = None


class RequestParams(CreateMessageRequestParams):
    """
    Parameters to configure the AugmentedLLM 'generate' requests.
    """

    messages: List[SamplingMessage] = Field(exclude=True, default=[])
    maxTokens: int = 2048
    model: str | None = None
    use_history: bool = True
    max_iterations: int = 20
    parallel_tool_calls: bool = True
    response_format: Any | None = None
    template_vars: Dict[str, Any] = Field(default_factory=dict)

    # This line must be at the same indentation as the other class variables
    model_config = {"arbitrary_types_allowed": True}
