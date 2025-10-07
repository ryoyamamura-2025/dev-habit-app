#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="dev-habit-app"
TAG="dev"
CONTAINER_NAME="${IMAGE_NAME}-container"

# --- 使い方を表示する関数 ---
usage() {
  echo "Usage: $0 [build|start|restart]"
  echo "  build:   Dockerイメージをビルドして、新しいコンテナを起動します。"
  echo "  start:   既存のコンテナを起動します。"
  echo "  restart: 既存のコンテナを再起動します。"
  exit 1
}

# --- メイン処理 ---
# 引数が指定されていない場合は使い方を表示
if [ $# -eq 0 ]; then
  usage
fi

# 第1引数に応じて処理を分岐
case "$1" in
  build)
    echo ">>> Building Docker image ${IMAGE_NAME}:${TAG} ..."
    docker buildx build \
      -f Dockerfile.dev \
      -t ${IMAGE_NAME}:${TAG} \
      .

    # 古いコンテナがあれば削除
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
      echo ">>> Removing old container..."
      docker rm -f ${CONTAINER_NAME}
    fi

    # 未使用のイメージを削除
    docker image prune -f

    echo ">>> Starting new container..."
    docker run -it \
      --name ${CONTAINER_NAME} \
      -p 3232:8080 \
      -v "$PWD":/workspace \
      -w /workspace/app \
      --env-file ./.env \
      ${IMAGE_NAME}:${TAG}
    ;;

  start|restart)
    echo ">>> Attempting to start/restart container: ${CONTAINER_NAME}"

    # 古いコンテナがあれば削除
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
      echo ">>> Removing old container..."
      docker rm -f ${CONTAINER_NAME}
    fi

    echo ">>> Starting new container..."
    docker run -it \
      --name ${CONTAINER_NAME} \
      -p 3232:8080 \
      -v "$PWD":/workspace \
      -w /workspace/app \
      --env-file ./.env \
      ${IMAGE_NAME}:${TAG} \
      /bin/bash
    ;;

  *)
    # build, start, restart以外の引数が指定された場合
    echo "!!! Invalid command: $1"
    usage
    ;;
esac
