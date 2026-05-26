"""FastAPI 应用入口"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI

# 加载环境变量
load_dotenv()

# 导入app（在加载环境变量之后）
from api.main import app

# 配置应用
app.title = os.getenv("APP_NAME", "LegalShield Agent")
app.version = os.getenv("APP_VERSION", "1.0.0")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
