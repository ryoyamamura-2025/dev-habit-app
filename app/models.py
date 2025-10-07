from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class ThreadPost(BaseModel):
    """
    スレッドへの投稿を表すモデル
    """
    post_id: int = Field(..., description="投稿ID (スレッド内で連番)")
    author: str = Field(..., description="投稿者名")
    message: str = Field(..., description="投稿内容")
    created_at: datetime = Field(default_factory=datetime.now, description="投稿日時")

class Thread(BaseModel):
    """
    スレッド全体を表すモデル
    """
    id: Optional[str] = Field(None, description="FirestoreのドキュメントID")
    title: str = Field(..., description="スレッドのタイトル")
    posts: List[ThreadPost] = Field(..., description="投稿のリスト")
    created_at: datetime = Field(default_factory=datetime.now, description="スレッド作成日時")
    updated_at: datetime = Field(default_factory=datetime.now, description="スレッド更新日時")
    is_generating: bool = Field(default=False, description="AIレスポンス生成中フラグ")

class CreateThreadRequest(BaseModel):
    """
    スレッド作成APIのリクエストボディ
    """
    title: str = Field(..., description="スレッドのタイトル", min_length=1, max_length=100)
    message: str = Field(..., description="最初の投稿内容", min_length=1, max_length=1000)

class CreatePostRequest(BaseModel):
    """
    投稿作成APIのリクエストボディ
    """
    message: str = Field(..., description="投稿内容", min_length=1, max_length=1000)
