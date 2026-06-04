import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.routes import router as rag_router
from apps.customer_service import customer_service_router

# 鏂囦欢涓婁紶澶у皬闄愬埗锛?0MB锛?
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app = FastAPI(
    title="RAG 鏅鸿兘闂瓟绯荤粺",
    version="2.0",
    description="鍩轰簬 ReAct Agent 鐨勬櫤鑳介棶绛旂郴缁燂紝鏀寔鐭ヨ瘑搴撴绱㈠拰瀵硅瘽绠＄悊"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8081", "http://127.0.0.1:8081", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 闈欐€佹枃浠舵湇鍔?
app.mount("/static", StaticFiles(directory="static"), name="static")

# 娉ㄥ唽璺敱
app.include_router(rag_router, prefix="/rag", tags=["RAG 妫€绱㈡湇鍔?])
app.include_router(customer_service_router)


@app.get("/", tags=["棣栭〉"])
async def root():
    """鏍圭鐐?- 鏈嶅姟淇℃伅"""
    return {
        "鍚嶇О": "RAG 鏅鸿兘闂瓟绯荤粺",
        "鐗堟湰": "2.0",
        "鏂囨。": "/docs",
        "鍓嶇椤甸潰": "/static/index.html",
        "鎻忚堪": "鍩轰簬 ReAct Agent 鐨勬櫤鑳介棶绛旂郴缁?,
        "绔偣": {
            "rag": {
                "POST /rag/search": "鎼滅储 FAQ锛圥OST鏂瑰紡锛?,
                "POST /rag/search/summary": "鎼滅储骞剁敓鎴愭€荤粨锛圥OST鏂瑰紡锛?,
                "GET /rag/documents": "鍒楀嚭鏂囨。",
                "POST /rag/documents": "娣诲姞鏂囨。"
            },
            "customer_service": {
                "POST /api/v1/chat": "涓庢櫤鑳藉鏈嶅璇?,
                "GET /api/v1/conversations": "鍒楀嚭浼氳瘽",
                "GET /api/v1/conversations/{id}": "鑾峰彇浼氳瘽璇︽儏",
                "DELETE /api/v1/conversations/{id}": "鍒犻櫎浼氳瘽"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8081)