from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from typing import List, Optional
import random
import asyncio
import os

from models import CreateThreadRequest, Thread, ThreadPost, CreatePostRequest, ThreadStatus
from services.firestore_service import db
from google.cloud import firestore


# AI関連のインポート
from services.gemini_service import geminiApiCaller, geminiApiCallerWithTool
from services.prompt import NANASHI_BASE_PROMPT, KAISUTSU_NIKI_PROMPT, NANASHI_REP_PROMPT, NANASHI_MULTI_PROMPT, NANASHI_MULTI_SYSTEM_INSTRUCTION
from services.json_schema import KAISUTSU_NIKI_SCHEMA, NANASHI_MULTI_RESPONSE_SCHEMA

router = APIRouter()
GCP_FIRESTORE_DB_NAME=os.getenv("GCP_FIRESTORE_DB_NAME")

# --- バックグラウンドタスク: AIレスポンス生成 ---
async def generate_ai_responses(thread_id: str, user_post_message: str, thread_title: str):
    """
    AIレスポンスを生成し、Firestoreに保存する
    """
    db = firestore.AsyncClient(database=GCP_FIRESTORE_DB_NAME)
    thread_ref = db.collection("threads").document(thread_id)

    try:
        # is_generatingフラグをTrueに設定
        await thread_ref.update({"is_generating": True})

        # ユーザーの投稿が質問形式か判定
        is_question = user_post_message.strip().endswith(("?", "？"))

        if is_question:
            # --- 解説ニキの処理 ---
            caller = geminiApiCallerWithTool(model_name="gemini-2.5-flash", response_schema=KAISUTSU_NIKI_SCHEMA, thinking_budget=-1)
            prompt = KAISUTSU_NIKI_PROMPT.format(user_post=user_post_message)
            parsed, error = await caller.atext2text(prompt)
            
            if error:
                kaisetsu_message = "すまん、ちょっと調子が悪いみたいだ。後でまた試してみてくれ。"
                new_posts = [{"author": "解説ニキ", "message": kaisetsu_message}]
            else:
                kaisetsu_message = parsed.get('response', 'わしにもわからん。あほじゃけえ')
                # リアクションする名無しさんを1体生成
                nanashi_caller = geminiApiCaller(model_name="gemini-2.5-flash-lite", thinking_budget=0)
                emotion = "太鼓持ち" # 解説ニキの後は太鼓持ちで固定
                nanashi_prompt = NANASHI_REP_PROMPT.format(emotion=emotion, thread_title=thread_title, user_post=kaisetsu_message)
                nanashi_message, nanashi_error = await nanashi_caller.atext2text(nanashi_prompt)
                
                if nanashi_error:
                    nanashi_message = "せやな"

                new_posts = [
                    {"author": "解説ニキ", "message": kaisetsu_message},
                    {"author": "名無しさん", "message": nanashi_message}
                ]

        else:
            # --- 名無しさんの処理（単一API呼び出し） ---
            num_responses = 3
            # TODO: thinking_budgetは適切な値に調整
            caller = geminiApiCaller(model_name="gemini-2.5-flash", response_schema=NANASHI_MULTI_RESPONSE_SCHEMA, thinking_budget=-1)
            
            # 過去の投稿履歴を取得
            snapshot = await thread_ref.get()
            thread_data = snapshot.to_dict() if snapshot.exists else {}
            posts = sorted(thread_data.get("posts", []), key=lambda p: p.get('post_id', 0))

            if posts:
                thread_history_lines = []
                for post in posts:
                    created_at = post.get('created_at')
                    time_str = ""
                    # Firestoreから取得したタイムスタンプはdatetimeオブジェクトの場合と、文字列の場合があるため両対応
                    if isinstance(created_at, datetime):
                        time_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(created_at, str):
                        # ISOフォーマットの文字列をパースする想定
                        try:
                            time_str = datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            time_str = created_at # パース失敗時は元の文字列をそのまま利用
                    
                    author = post.get('author', '不明')
                    message = post.get('message', '')
                    thread_history_lines.append(f"{author} ({time_str}): {message}")
                thread_history = "\n".join(thread_history_lines)
            else:
                # 履歴が取得できない場合は、現在の投稿を履歴とする
                # この場合、正確な時間は不明なため含めない
                thread_history = f"イッチ: {user_post_message}"
            
            prompt = NANASHI_MULTI_PROMPT.format(
                num_replies=num_responses,
                thread_title=thread_title,
                thread_history=thread_history, # 本来は完全な履歴
                latest_post_content=user_post_message
            )
            print(prompt)
            # システムインストラクションをプロンプトに含める
            full_prompt = f"{NANASHI_MULTI_SYSTEM_INSTRUCTION.format(num_replies=num_responses)}\n\n{prompt}"

            parsed_responses, error = await caller.atext2text(full_prompt)

            if error or not parsed_responses:
                # エラー時やレスポンスがない場合は固定の代替レスポンス
                new_posts = [
                    {"author": "名無しさん", "message": "せやな"},
                    {"author": "名無しさん", "message": "草"},
                    {"author": "名無しさん", "message": "なるほど"},
                ]
            else:
                new_posts = [
                    {"author": "名無しさん", "message": item.get('content', '...')} for item in parsed_responses
                ]

        # AIが何も生成しなかった場合は書き込まない
        if not new_posts:
            return # finallyは実行される
        
        snapshot = await thread_ref.get()
        if not snapshot.exists:
            return

        thread_data = snapshot.to_dict()
        current_post_count = len(thread_data.get("posts", []))
        
        # 最終的な書き込みデータを作成（post_idなどを付与）
        final_posts_data = []
        for i, post_content in enumerate(new_posts):
            final_post = {
                "post_id": current_post_count + i + 1,
                "author": post_content["author"],
                "message": post_content["message"],
                "created_at": datetime.now()
            }
            final_posts_data.append(final_post)
        
        # 1回のupdateで全ての投稿をまとめて追加
        await thread_ref.update({
            "posts": firestore.ArrayUnion(final_posts_data),
            "updated_at": firestore.SERVER_TIMESTAMP
        })

    except Exception as e:
        print(f"AIレスポンス生成中にエラーが発生しました: {e}")
        # エラーが発生してもフラグは下ろす
    finally:
        # is_generatingフラグをFalseに設定
        await thread_ref.update({"is_generating": False})


# --- APIエンドポイント ---
@router.post("/api/threads", response_model=Thread)
async def create_thread(thread_data: CreateThreadRequest, background_tasks: BackgroundTasks):
    """
    新しいスレッドを作成し、AIレスポンス生成タスクを開始する
    """
    try:
        now = datetime.now()
        first_post = ThreadPost(post_id=1, author="イッチ", message=thread_data.message, created_at=now)
        new_thread = Thread(title=thread_data.title, posts=[first_post], created_at=now, updated_at=now, is_generating=False)
        
        thread_dict = new_thread.model_dump(exclude={"id"})
        doc_ref_tuple = await db.collection("threads").add(thread_dict)
        thread_id = doc_ref_tuple[1].id
        
        created_thread = new_thread.model_copy(update={"id": thread_id})

        # バックグラウンドでAIレスポンスを生成
        background_tasks.add_task(generate_ai_responses, thread_id, thread_data.message, thread_data.title)
        
        return created_thread
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/threads/{thread_id}/posts", response_model=ThreadPost)
async def create_post_in_thread(thread_id: str, post_data: CreatePostRequest, background_tasks: BackgroundTasks):
    """
    指定されたスレッドに新しい投稿を追加し、AIレスポンス生成タスクを開始する
    """
    try:
        db = firestore.AsyncClient(database=GCP_FIRESTORE_DB_NAME)
        doc_ref = db.collection("threads").document(thread_id)
        
        doc = await doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        thread_data = doc.to_dict()
        thread_title = thread_data.get("title", "") # バックグラウンドタスク用にタイトルを取得
        new_post_id = len(thread_data.get("posts", [])) + 1
        
        # Pydanticモデルなどを使って新しい投稿データを作成
        new_post = ThreadPost(
            post_id=new_post_id,
            author="イッチ",
            message=post_data.message,
            created_at=datetime.now()
        )
            
        # トランザクションオブジェクトを使ってドキュメントを更新
        await doc_ref.update({
            "posts": firestore.ArrayUnion([new_post.model_dump()]),
            "updated_at": firestore.SERVER_TIMESTAMP # サーバー時刻の使用を推奨
        })

        # バックグラウンドでAIレスポンスを生成
        background_tasks.add_task(generate_ai_responses, thread_id, post_data.message, thread_title)

        return new_post

    except HTTPException as e:
        # 404エラーなどをそのままクライアントに返す
        raise e
    except Exception as e:
        # その他の予期せぬエラー
        print(f"An unexpected error occurred: {e}") # サーバーログにエラーを出力
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

# --- 既存の読み取り系エンドポイント (変更なし) ---
@router.get("/api/threads", response_model=List[Thread])
async def get_threads():
    # ... (変更なし)
    try:
        threads = []
        docs = db.collection("threads").stream()
        async for doc in docs:
            thread_data = doc.to_dict()
            thread_data["id"] = doc.id
            threads.append(Thread(**thread_data))
        return threads
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/threads/{thread_id}", status_code=200)
async def delete_thread(thread_id: str):
    # ... (変更なし)
    try:
        doc_ref = db.collection("threads").document(thread_id)
        doc = await doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Thread not found")
        await doc_ref.delete()
        return {"message": f"Thread {thread_id} deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/threads/{thread_id}/posts", response_model=List[ThreadPost])
async def get_posts_in_thread(thread_id: str, since: Optional[int] = None):
    # ... (変更なし)
    try:
        doc_ref = db.collection("threads").document(thread_id)
        doc = await doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Thread not found")
        thread = Thread(**doc.to_dict())
        
        if since is not None:
            # 'since' より新しい投稿のみをフィルタリング
            new_posts = [p for p in thread.posts if p.post_id > since]
            sorted_posts = sorted(new_posts, key=lambda p: p.post_id)
        else:
            # sinceがなければ全件取得（既存の動作）
            sorted_posts = sorted(thread.posts, key=lambda p: p.post_id)
            
        return sorted_posts
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/threads/{thread_id}/status", response_model=ThreadStatus)
async def get_thread_status(thread_id: str):
    try:
        doc_ref = db.collection("threads").document(thread_id)
        doc = await doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        thread_data = doc.to_dict()
        post_count = len(thread_data.get("posts", []))
        is_generating = thread_data.get("is_generating", False)
        
        return ThreadStatus(is_generating=is_generating, post_count=post_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))