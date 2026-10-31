"""
ASGI Entrypoint for Sahayak AI FastAPI Microservice.
Supports running:
    uvicorn main:app --reload
from within the backend directory.
"""
import sys
from pathlib import Path

# Ensure backend root is on Python path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

