import uuid
from typing import List, Optional, Dict, Any
from infrastructure.database import db_manager
from infrastructure.models import Message, Conversation


class ConversationManager:
    """浼氳瘽绠＄悊鍣?""

    def __init__(self):
        self.db = db_manager

    def create_conversation(self, user_id: Optional[str] = None, title: Optional[str] = None) -> Conversation:
        user_id = user_id or "anonymous"
        """鍒涘缓鏂颁細璇?""
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title
        )

        # 淇濆瓨鍒版暟鎹簱
        self.db.execute(
            '''INSERT INTO conversations (conversation_id, user_id, title)
               VALUES (?, ?, ?)''',
            (conversation_id, user_id, title)
        )

        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """鑾峰彇浼氳瘽"""
        row = self.db.fetch_one(
            '''SELECT * FROM conversations WHERE conversation_id = ?''',
            (conversation_id,)
        )

        if not row:
            return None

        conversation = Conversation.from_dict(dict(row))

        # 鑾峰彇娑堟伅
        messages = self.db.fetch_all(
            '''SELECT * FROM messages WHERE conversation_id = ? ORDER BY turn_number''',
            (conversation_id,)
        )

        for msg_row in messages:
            msg_data = dict(msg_row)
            message = Message(
                role=msg_data["role"],
                content=msg_data["content"],
                turn_number=msg_data["turn_number"]
            )
            conversation.add_message(message)

        return conversation

    def add_message(self, conversation_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """娣诲姞娑堟伅鍒颁細璇?""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        # 鑾峰彇涓嬩竴涓?turn_number
        messages = self.db.fetch_all(
            '''SELECT turn_number FROM messages WHERE conversation_id = ? ORDER BY turn_number DESC LIMIT 1''',
            (conversation_id,)
        )

        turn_number = 1
        if messages:
            turn_number = messages[0]["turn_number"] + 1

        # 淇濆瓨娑堟伅鍒版暟鎹簱
        cursor = self.db.execute(
            '''INSERT INTO messages (conversation_id, role, content, turn_number, metadata)
               VALUES (?, ?, ?, ?, ?)''',
            (conversation_id, role, content, turn_number, str(metadata) if metadata else None)
        )

        return cursor.lastrowid

    def list_conversations(self, user_id: Optional[str] = None, limit: int = 20) -> List[Conversation]:
        user_id = user_id or "anonymous"
        """鍒楀嚭浼氳瘽鍒楄〃"""
        if user_id:
            rows = self.db.fetch_all(
                '''SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?''',
                (user_id, limit)
            )
        else:
            rows = self.db.fetch_all(
                '''SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?''',
                (limit,)
            )

        conversations = []
        for row in rows:
            conv = Conversation.from_dict(dict(row))
            conversations.append(conv)

        return conversations

    def delete_conversation(self, conversation_id: str) -> bool:
        """鍒犻櫎浼氳瘽"""
        # 鍒犻櫎娑堟伅
        self.db.execute(
            '''DELETE FROM messages WHERE conversation_id = ?''',
            (conversation_id,)
        )

        # 鍒犻櫎浼氳瘽
        cursor = self.db.execute(
            '''DELETE FROM conversations WHERE conversation_id = ?''',
            (conversation_id,)
        )

        return cursor.rowcount > 0

    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """鏇存柊浼氳瘽鏍囬"""
        cursor = self.db.execute(
            '''UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?''',
            (title, conversation_id)
        )
        return cursor.rowcount > 0

    def get_conversation_title(self, conversation_id: str) -> Optional[str]:
        """鑾峰彇浼氳瘽鏍囬"""
        row = self.db.fetch_one(
            '''SELECT title FROM conversations WHERE conversation_id = ?''',
            (conversation_id,)
        )
        if row:
            return dict(row).get("title")
        return None


# 鍒涘缓鍗曚緥
conversation_manager = ConversationManager()

__all__ = ["ConversationManager", "conversation_manager"]
