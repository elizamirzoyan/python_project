"""
DataSnoop - Run with: python main.py
"""
import uvicorn

if __name__ == "__main__":
    print("🔍 DataSnoop is starting up...")
    print("=" * 50)
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],  # only watch app/ — ignores venv, data, etc.
    )
