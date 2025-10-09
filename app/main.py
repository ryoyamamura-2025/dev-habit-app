from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
import uvicorn
import os

from controller import router

# --- アプリケーション設定 ---
app = FastAPI(title="Habit App")

secret_key = os.urandom(24)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
app.add_middleware(SessionMiddleware, secret_key=secret_key)

client_id = os.environ.get("GOOGLE_CLIENT_ID")
client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

# 2. Flow.from_client_config に渡すための設定辞書を作成
client_config = {
    "web": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = Flow.from_client_config(
    client_config=client_config,
    scopes=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email"
    ],
    redirect_uri="https://habit-app-897239585193.us-central1.run.app/callback"
)

# APIルーターを登録
app.include_router(router)

# 静的ファイルの配信
app.mount("/static", StaticFiles(directory="static"), name="static")

# ルートパスでindex.htmlを返す
@app.get("/", include_in_schema=False, name="index")
async def read_index(request: Request):

    # セッションにユーザー情報がなければログインページへリダイレクト
    user_info = request.session.get('user')

    if not user_info:
        return RedirectResponse(url=request.url_for('login'))

    return FileResponse('static/index.html')

@app.get("/login", name="login")
async def login(request: Request):
    """
    Googleの認証ページにリダイレクトする。
    """
    # 認証URLとCSRF対策用のstateを生成
    authorization_url, state = flow.authorization_url()
    
    # stateをセッションに保存
    request.session['state'] = state
    
    return RedirectResponse(authorization_url)

@app.get("/callback")
async def callback(request: Request):
    """
    Googleからのリダイレクトを受け取り、認証処理を行う。
    """
    # CSRF対策: リクエストのstateとセッションのstateを比較
    state_from_google = request.query_params.get('state')
    state_from_session = request.session.get('state')
    
    if not state_from_google or state_from_google != state_from_session:
        return HTMLResponse("State mismatch error", status_code=400)
    
    # 認証コードを使ってトークンを取得
    # request.urlはURLオブジェクトなので文字列に変換する
    flow.fetch_token(authorization_response=str(request.url))
    
    # 取得した認証情報（credentials）からIDトークンを取得
    credentials = flow.credentials
    id_info = id_token.verify_oauth2_token(
        id_token=credentials.id_token,
        request=google_requests.Request(),
        audience=credentials.client_id,
    )

    # ユーザー情報をセッションに保存
    request.session['user'] = {
        'id': id_info.get("sub"),
        'name': id_info.get("name"),
        'email': id_info.get("email"),
    }
    
    return RedirectResponse(url=request.url_for('index'))

@app.get("/logout", name="logout")
async def logout(request: Request):
    """
    セッションからユーザー情報を削除し、ログアウトする。
    """
    request.session.pop('user', None)
    return RedirectResponse(url=request.url_for('login'))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
