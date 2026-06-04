from typing import List, Dict, Any, Callable, Optional


class ToolParameter:
    """鎻忚堪宸ュ叿鐨勪竴涓緭鍏ュ弬鏁?""
    
    def __init__(self, name: str, type: str, description: str, required: bool = True, default: Any = None):
        self.name = name
        self.type = type
        self.description = description
        self.required = required
        self.default = default


class Tool:
    """瀵圭函鍑芥暟鐨勮杽灏佽锛屼緵 Agent 鎸夊悕绉拌皟搴?""
    
    def __init__(self, name: str, description: str, func: Callable, parameters: List[ToolParameter]):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters
    
    def run(self, params: Dict[str, Any]) -> str:
        """Agent 鐨勫敮涓€璋冪敤鍏ュ彛"""
        # 鍙傛暟楠岃瘉
        for param in self.parameters:
            if param.required and param.name not in params:
                if param.default is not None:
                    params[param.name] = param.default
                else:
                    raise ValueError(f"Missing required parameter: {param.name}")
        
        # 璋冪敤鍘熷鍑芥暟
        return self.func(**params)
    
    def to_prompt_desc(self) -> str:
        """鐢熸垚娉ㄥ叆 prompt 鐨勫伐鍏锋弿杩版枃鏈?""
        param_descs = []
        for param in self.parameters:
            required_mark = "" if param.required else " (鍙€?"
            default_mark = f" = {param.default}" if param.default is not None else ""
            param_descs.append(f"{param.name}: {param.type}{required_mark}{default_mark}")
        
        return f"- {self.name}({', '.join(param_descs)}): {self.description}"
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """[棰勭暀] 杞崲涓?OpenAI function calling 鏍煎紡"""
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