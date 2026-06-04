from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
import json as _json
from domain.customer_service import customer_service_agent
from utils import conversation_manager
from utils.auth import get_current_user, hash_password, verify_password, create_access_token
from infrastructure.database import db_manager
from infrastructure.models import Message

router = APIRouter(prefix="/api/v1", tags=["鏅鸿兘瀹㈡湇"])



class AuthRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class AuthResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")


class ChatRequest(BaseModel):
    question: str = Field(..., description="鐢ㄦ埛闂")
    conversation_id: Optional[str] = Field(None, description="浼氳瘽ID锛堝彲閫夛紝涓嶆彁渚涘垯鍒涘缓鏂颁細璇濓級")
    sources: Optional[List[dict]] = Field(None, description="鐭ヨ瘑搴撴潵婧愪俊鎭?)
    reply: Optional[str] = Field(None, description="鐩存帴淇濆瓨鐨勫洖澶嶏紙涓嶇粡杩?agent 鐢熸垚锛?)


class ChatResponse(BaseModel):
    conversation_id: str = Field(..., description="浼氳瘽ID")
    reply: str = Field(..., description="瀹㈡湇鍥炲")
    thinking: Optional[str] = Field(None, description="鎬濊€冭繃绋?)
    action: Optional[str] = Field(None, description="鎵ц鐨勫姩浣?)
    title: Optional[str] = Field(None, description="浼氳瘽鏍囬")
    rewritten_question: Optional[str] = Field(None, description="閲嶅啓鍚庣殑闂")
    final_prompt: Optional[str] = Field(None, description="LLM瀹屾暣Prompt涓婁笅鏂?)
    message_id: Optional[int] = Field(None, description="娑堟伅ID")


class ConversationListResponse(BaseModel):
    conversations: List[dict] = Field(..., description="浼氳瘽鍒楄〃")


class ConversationDetailResponse(BaseModel):
    conversation_id: str = Field(..., description="浼氳瘽ID")
    title: str = Field(..., description="浼氳瘽鏍囬")
    messages: List[dict] = Field(..., description="娑堟伅鍒楄〃")


@router.post("/chat", response_model=ChatResponse, summary="涓庢櫤鑳藉鏈嶅璇?)
async def chat(request: ChatRequest, user_id: str = Depends(get_current_user)):
    """
    涓庢櫤鑳藉鏈嶅璇?

    鍙傛暟锛?
        question: 鐢ㄦ埛闂
        conversation_id: 浼氳瘽ID锛堝彲閫夛紝涓嶆彁渚涘垯鍒涘缓鏂颁細璇濓級

    杩斿洖锛?
        瀹㈡湇鍥炲
    """
    try:
        conversation_id = request.conversation_id

        if conversation_id:
            conversation = conversation_manager.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="浼氳瘽涓嶅瓨鍦?)
            history = conversation.get_messages_for_llm()
        else:
            conversation = conversation_manager.create_conversation(user_id=user_id)
            conversation_id = conversation.conversation_id
            history = None

        if request.reply is not None:
            result_reply = request.reply
            result_thinking = None
            result_action = None
            result_rewritten_question = None
            result_final_prompt = None
        else:
            result = customer_service_agent.run(request.question, history)
            result_reply = result["reply"]
            result_thinking = result.get("thinking")
            result_action = result.get("action")
            result_rewritten_question = result.get("rewritten_question")
            result_final_prompt = result.get("final_prompt")

        conversation_manager.add_message(conversation_id, "user", request.question)
        assistant_msg_id = conversation_manager.add_message(
            conversation_id,
            "assistant",
            result_reply,
            metadata={"sources": request.sources} if request.sources else None
        )

        # Auto-generate title with LLM for first exchange
        is_first_turn = not (history and len(history) >= 2)
        title = request.question[:50] if len(request.question) > 50 else request.question
        if is_first_turn:
            try:
                generated = customer_service_agent._generate_title(request.question, result_reply)
                if generated and generated.strip():
                    title = generated
            except Exception:
                pass
        conversation_manager.update_conversation_title(conversation_id, title)

        updated_conversation = conversation_manager.get_conversation(conversation_id)

        return ChatResponse(
            conversation_id=conversation_id,
            reply=result_reply,
            thinking=result_thinking,
            action=result_action,
            title=updated_conversation.title if updated_conversation else title,
            rewritten_question=result_rewritten_question,
            final_prompt=result_final_prompt,
            message_id=assistant_msg_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations", response_model=ConversationListResponse, summary="鍒楀嚭鎵€鏈変細璇?)
async def list_conversations(limit: int = Query(20, description="杩斿洖鏁伴噺闄愬埗"), user_id: str = Depends(get_current_user)):
    """鍒楀嚭鎵€鏈変細璇?""
    try:
        conversations = conversation_manager.list_conversations(user_id=user_id, limit=limit)
        return ConversationListResponse(
            conversations=[conv.to_dict() for conv in conversations]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse, summary="鑾峰彇浼氳瘽璇︽儏")
async def get_conversation(conversation_id: str):
    """鑾峰彇浼氳瘽璇︽儏"""
    try:
        conversation = conversation_manager.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="浼氳瘽涓嶅瓨鍦?)

        return ConversationDetailResponse(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            messages=[msg.to_dict() for msg in conversation.messages]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}", summary="鍒犻櫎浼氳瘽")
async def delete_conversation(conversation_id: str):
    """鍒犻櫎浼氳瘽"""
    try:
        success = conversation_manager.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="浼氳瘽涓嶅瓨鍦?)
        return {"success": True, "message": "浼氳瘽宸插垹闄?}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/conversations/{conversation_id}/title", summary="鏇存柊浼氳瘽鏍囬")
async def update_conversation_title(conversation_id: str, title: str = Query(..., description="鏂版爣棰?)):
    """鏇存柊浼氳瘽鏍囬"""
    try:
        success = conversation_manager.update_conversation_title(conversation_id, title)
        if not success:
            raise HTTPException(status_code=404, detail="浼氳瘽涓嶅瓨鍦?)
        return {"success": True, "message": "鏍囬宸叉洿鏂?, "title": title}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream", summary="涓庢櫤鑳藉鏈嶅璇濓紙娴佸紡锛?)
async def chat_stream(request: ChatRequest, user_id: str = Depends(get_current_user)):
    """Streaming SSE chat endpoint."""
    try:
        conversation_id = request.conversation_id

        if conversation_id:
            conversation = conversation_manager.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="浼氳瘽涓嶅瓨鍦?)
            history = conversation.get_messages_for_llm()
        else:
            conversation = conversation_manager.create_conversation(user_id=user_id)
            conversation_id = conversation.conversation_id
            history = None

        async def sse_generator():
            full_reply_parts = []
            sources_data = None
            is_first = True

            for event in customer_service_agent.run_stream(request.question, history):
                event_type = event["event"]
                event_data = event["data"]

                if event_type == "done":
                    full_reply = event_data.get("reply", "")
                    sources_data = event_data.get("sources", [])

                    # Persist messages
                    conversation_manager.add_message(conversation_id, "user", request.question)
                    assistant_msg_id = conversation_manager.add_message(
                        conversation_id,
                        "assistant",
                        full_reply,
                        metadata={"sources": sources_data} if sources_data else None,
                    )

                    # Auto-generate title
                    is_first_turn = not (history and len(history) >= 2)
                    title = request.question[:50] if len(request.question) > 50 else request.question
                    if is_first_turn:
                        try:
                            generated = customer_service_agent._generate_title(request.question, full_reply)
                            if generated and generated.strip():
                                title = generated
                        except Exception:
                            pass
                    conversation_manager.update_conversation_title(conversation_id, title)

                    done_data = {
                        "conversation_id": conversation_id,
                        "title": title,
                        "message_id": assistant_msg_id,
                        "reply": full_reply,
                        "sources": sources_data,
                    }
                    if event_data.get("rewritten_question"):
                        done_data["rewritten_question"] = event_data["rewritten_question"]

                    yield f"event: done\ndata: {_json.dumps(done_data, ensure_ascii=False)}\n\n"
                    break

                yield f"event: {event_type}\ndata: {_json.dumps(event_data, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/{conversation_id}/feedback", summary="鎻愪氦娑堟伅鍙嶉锛堢偣璧?鐐硅俯锛?)
async def submit_feedback(conversation_id: str, message_id: int = Query(..., description="娑堟伅ID"), rating: str = Query(..., description="like 鎴?dislike")):
    """Submit feedback for a specific message."""
    if rating not in ("like", "dislike"):
        raise HTTPException(status_code=400, detail="rating must be 'like' or 'dislike'")
    try:
        db_manager.add_feedback(conversation_id, message_id, rating)
        return {"success": True, "message": "鍙嶉宸叉彁浜?}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/{conversation_id}/feedback", summary="鑾峰彇浼氳瘽鍙嶉")
async def get_feedback(conversation_id: str):
    """Get feedback records for a conversation."""
    try:
        records = db_manager.get_feedback(conversation_id)
        return {"conversation_id": conversation_id, "feedback": [dict(r) for r in records]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Authentication Endpoints =====

@router.post("/auth/register", response_model=AuthResponse, summary="Register new user")
async def register(request: AuthRequest):
    import uuid as _uuid
    existing = db_manager.get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user_id = str(_uuid.uuid4())
    pw_hash = hash_password(request.password)
    success = db_manager.add_user(user_id, request.username, pw_hash)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create user")

    token = create_access_token(user_id)
    return AuthResponse(access_token=token, user_id=user_id, username=request.username)


@router.post("/auth/login", response_model=AuthResponse, summary="Login")
async def login(request: AuthRequest):
    user = db_manager.get_user_by_username(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user["user_id"])
    return AuthResponse(access_token=token, user_id=user["user_id"], username=request.username)


@router.get("/auth/me", summary="Get current user info")
async def me(user_id: str = Depends(get_current_user)):
    if user_id == "anonymous":
        return {"user_id": "anonymous", "username": "anonymous"}
    user = db_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user["user_id"], "username": user["username"]}

