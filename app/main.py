from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

from controller import router

# --- アプリケーション設定 ---
app = FastAPI(title="Habit App")

# APIルーターを登録
app.include_router(router)

# 静的ファイルの配信
app.mount("/static", StaticFiles(directory="static"), name="static")

# ルートパスでindex.htmlを返す
@app.get("/", include_in_schema=False)
async def read_index():
    return FileResponse('static/index.html')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
