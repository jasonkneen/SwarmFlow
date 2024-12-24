from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from typing import List, Callable, Union, Optional, Any

# Third-party imports
from pydantic import BaseModel

# AgentFunction = Union[str, Callable[[], Union[str, "Agent", dict]]]


class Agent(BaseModel):
    name: str = "Agent"
    description: str = "Description"
    model: str = "gpt-4o"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[dict] = []
    tool_choice: Optional[Union[dict[str, Any], str]] = None
    parallel_tool_calls: bool = True


class Response(BaseModel):
    messages: List = []
    agent: Optional[Agent] = None
    context_variables: dict = {}


class Result(BaseModel):
    """
    Encapsulates the possible return values for an agent function.

    Attributes:
        value (str): The result value as a string.
        agent (Agent): The agent instance, if applicable.
        context_variables (dict): A dictionary of context variables.
    """

    value: str = ""
    agent: Optional[Agent] = None
    context_variables: dict = {}
