from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """
    User ka command jo Agent Brain ko diya jayega.
    """

    message: str

    session_id: Optional[str] = None


class AgentPlan(BaseModel):
    """
    Agent ne user command ko samajhne ke baad jo plan banaya.
    """

    goal: str

    steps: List[str] = Field(
        default_factory=list
    )


class ToolCall(BaseModel):
    """
    Agent kisi tool ko execute karne ke liye
    jo request banayega.
    """

    tool_name: str

    arguments: Dict[str, Any] = Field(
        default_factory=dict
    )


class ToolResult(BaseModel):
    """
    Tool execution ka result.
    """

    tool_name: str

    success: bool

    result: Any = None

    error: Optional[str] = None


class AgentResponse(BaseModel):
    """
    Agent ka final structured response.
    """

    success: bool

    message: str

    plan: Optional[AgentPlan] = None

    tool_calls: List[ToolCall] = Field(
        default_factory=list
    )

    tool_results: List[ToolResult] = Field(
        default_factory=list
    )