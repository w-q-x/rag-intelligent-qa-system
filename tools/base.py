
from typing import List, Dict, Any, Callable, Optional


class ToolParameter:
    """Parameter definition for tools"""
    
    def __init__(self, name: str, type: str, description: str, required: bool = True, default: Any = None):
        self.name = name
        self.type = type
        self.description = description
        self.required = required
        self.default = default


class Tool:
    """Base class for tools that can be used by the Agent"""
    
    def __init__(self, name: str, description: str, func: Callable, parameters: List[ToolParameter]):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters
    
    def run(self, params: Dict[str, Any]) -> str:
        """Execute the tool with given parameters"""
        # Validate parameters
        for param in self.parameters:
            if param.required and param.name not in params:
                if param.default is not None:
                    params[param.name] = param.default
                else:
                    raise ValueError(f"Missing required parameter: {param.name}")
        
        # Execute the function
        return self.func(**params)
    
    def to_prompt_desc(self) -> str:
        """Convert tool to a prompt description string"""
        param_descs = []
        for param in self.parameters:
            required_mark = "" if param.required else " (optional)"
            default_mark = f" = {param.default}" if param.default is not None else ""
            param_descs.append(f"{param.name}: {param.type}{required_mark}{default_mark}")
        
        return f"- {self.name}({', '.join(param_descs)}): {self.description}"
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """[Optional] Convert to OpenAI function calling format"""
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in self.parameters:
            parameters["properties"][param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                parameters["required"].append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters
        }

