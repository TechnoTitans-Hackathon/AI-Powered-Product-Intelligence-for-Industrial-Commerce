import logging
import json
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Centralized registry for AI engine tools.
    
    Provides strict schema validation and execution boundaries between
    the AI planner/agents and the backend systems.
    
    Prevents hallucinated tool calls and unexpected parameters.
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        
        # We define schemas for allowed tools
        self._schemas = {
            "vector_search": {
                "description": "Search the internal knowledge base for evidence.",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "filters": {"type": "dict", "required": False}
                }
            },
            "web_acquire": {
                "description": "Perform external research and acquire knowledge from the web.",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "target_attributes": {"type": "list", "required": False}
                }
            }
        }

    def register_tool(self, name: str, handler: Callable, description: Optional[str] = None, schema: Optional[dict] = None):
        """Register a backend handler to an AI tool name."""
        if schema:
            self._schemas[name] = schema
        elif name not in self._schemas:
            logger.warning(f"ToolRegistry: Registering undocumented tool '{name}'")
            
        self._tools[name] = {
            "handler": handler,
            "description": description or self._schemas.get(name, {}).get("description", "Unknown tool")
        }
        logger.info(f"ToolRegistry: Registered tool '{name}'")
        
    def register(self, name: str, handler: Callable, description: Optional[str] = None, schema: Optional[dict] = None):
        """Alias for register_tool."""
        return self.register_tool(name, handler, description, schema)
        
    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_available_tools(self) -> Dict[str, Any]:
        """Return the schema of available registered tools for LLM prompting."""
        available = {}
        for name in self._tools:
            if name in self._schemas:
                available[name] = self._schemas[name]
            else:
                available[name] = {"description": self._tools[name]["description"]}
        return available

    async def execute_tool(self, name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool with strict validation."""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' is not registered.")
            
        # Validate against schema if we have one
        if name in self._schemas and "request" not in parameters:
            schema = self._schemas[name]["parameters"]
            for param_name, param_def in schema.items():
                if param_def.get("required") and param_name not in parameters:
                    raise ValueError(f"Tool '{name}' missing required parameter '{param_name}'")
                    
                if param_name in parameters:
                    val = parameters[param_name]
                    expected_type = param_def.get("type")
                    
                    if expected_type == "string" and not isinstance(val, str):
                        raise ValueError(f"Tool '{name}' parameter '{param_name}' must be a string")
                    elif expected_type == "dict" and not isinstance(val, dict):
                        raise ValueError(f"Tool '{name}' parameter '{param_name}' must be a dict")
                    elif expected_type == "list" and not isinstance(val, list):
                        raise ValueError(f"Tool '{name}' parameter '{param_name}' must be a list")
                        
        logger.info(f"ToolRegistry: Executing tool '{name}'")
        handler = self._tools[name]["handler"]
        
        try:
            return await handler(**parameters)
        except Exception as e:
            logger.error(f"ToolRegistry: Tool '{name}' execution failed: {e}")
            raise
