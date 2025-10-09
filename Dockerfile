# Dockerfile
# 1) ベースイメージ：軽量な Python
FROM python:3.12-slim

# 2) uv（高速パッケージマネージャ）を取り込み
#    別イメージから /uv /uvx バイナリをコピーするワンライナー
COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /uvx /bin/

# 3) 作業ディレクトリ
WORKDIR /app

# 4) 依存だけインストール（中間レイヤ） 
#    Cloud run への Deploy 時は BuildKit が使えない
COPY pyproject.toml uv.lock /app/
RUN uv sync --locked --no-install-project

# 5) ここで初めてソースをコピー
COPY pyproject.toml uv.lock client_secret.json ./
COPY ./app ./
# 6) プロジェクト本体を editable で同期 
#    Cloud run への Deploy 時は BuildKit が使えない
RUN uv sync

# 7) Cloud Run は 8080 がデフォルトなので開けておく
EXPOSE 8080

# 8) コンテナ起動時のコマンド
#    uv 経由で uvicorn を実行。app.main:app を 0.0.0.0:8080 で起動
#    Deploy 時は ホットリロードは不要
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
