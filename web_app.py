"""故事创作助手 v3 — 入口文件"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routes import create_app
import uvicorn

app = create_app()

if __name__ == "__main__":
    print("🚀 故事创作助手 v3")
    print("🌐 http://localhost:8888")
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="info")
