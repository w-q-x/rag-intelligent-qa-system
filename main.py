import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.routes import router as rag_router
from apps.customer_service import customer_service_router

# 文件上传大小限制 - 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app = FastAPI(
    title="RAG 智能问答系统",
    version="2.0",
    description="基于 ReAct Agent 的智能客服系统，支持混合检索和 Small-to-Big 架构"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 路由注册
app.include_router(rag_router, prefix="/rag", tags=["RAG 接口"])
app.include_router(customer_service_router)


@app.get("/", tags=["根路径"])
async def root():
    """健康检查 - 重定向到前端"""
    return {
        "服务": "RAG 智能问答系统",
        "版本": "2.0",
        "文档": "/docs",
        "前端页面": "/static/index.html",
        "简介": "基于 ReAct Agent 的智能客服系统",
        "接口列表": {
            "rag": {
                "POST /rag/search": "检索知识库 (FAQ 模式)",
                "POST /rag/search/summary": "检索知识库并生成总结",
                "GET /rag/documents": "获取文档列表",
                "POST /rag/documents": "上传文档"
            },
            "customer_service": {
                "POST /api/v1/chat": "智能客服对话",
                "GET /api/v1/conversations": "获取对话列表",
                "GET /api/v1/conversations/{id}": "获取对话详情",
                "DELETE /api/v1/conversations/{id}": "删除对话"
            }
        }
    }




if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8080"))
    uvicorn.run("main:app", host="127.0.0.1", port=port)
