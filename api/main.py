import os
import sys
import uvicorn
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def main():
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8080"))

    uvicorn.run(
        "api.routes:app",
        host=host,
        port=port,
        reload=True
    )

if __name__ == "__main__":
    main()