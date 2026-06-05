from typing import List, Dict, Any, Optional
from datetime import datetime


class Message:
    """消息模型"""
    
    def __init__(self, role: str, content: str, turn_number: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None):
        self.role = role
        self.content = content
        self.turn_number = turn_number
        self.metadata = metadata or {}
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "role": self.role,
            "content": self.content,
            "turn_number": self.turn_number,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
        if self.metadata and self.metadata.get("sources"):
            result["sources"] = self.metadata["sources"]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            turn_number=data.get("turn_number"),
            metadata=data.get("metadata")
        )


class Conversation:
    """对话模型"""
    
    def __init__(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        messages: Optional[List[Message]] = None,
        status: str = "active"
    ):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.title = title or "新对话"
        self.messages = messages or []
        self.status = status
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_message(self, message: Message):
        """添加消息"""
        if not self.messages:
            message.turn_number = 1
        else:
            last_turn = max(m.turn_number for m in self.messages if m.turn_number is not None)
            message.turn_number = (last_turn or 0) + 1
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_messages_for_llm(self) -> List[Dict[str, str]]:
        """获取适合 LLM 的消息列表"""
        return [{"role": m.role, "content": m.content} for m in self.messages]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": len(self.messages)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        return cls(
            conversation_id=data["conversation_id"],
            user_id=data.get("user_id"),
            title=data.get("title"),
            status=data.get("status", "active")
        )


class User:
    def __init__(self, user_id: str, username: str):
        self.user_id = user_id
        self.username = username

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(user_id=data["user_id"], username=data["username"])


__all__ = ["Message", "Conversation", "User"]
