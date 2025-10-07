from fastapi import FastAPI
import uvicorn
import os

# --- アプリケーション設定 ---
app = FastAPI(title="Habit App")

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)