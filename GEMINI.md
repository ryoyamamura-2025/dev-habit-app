# 習慣化支援BBS作成プロジェクト
## プロジェクト概要
ユーザー（イッチ）が設定した習慣化目標に対し、複数のAIが2ちゃんねる風のチャットで絡むことで、楽しくモチベーションを維持することを支援するWebアプリケーション。

## 開発の進め方
- {## 開発計画}セクションに記載のMarkdownファイルに開発フェーズとToDoが列挙されています。  
- ToDoに従って開発を進めてください。  
- 各ToDoは{##機能要件、非機能要件}セクションに記載のMarkdownファイル内の要件定義IDと紐づいており、**ToDo実行の際に要件を必ず確認する**こと。

## 機能要件、非機能要件
`./docs/Requirements.md`に記載

## 開発計画
`./docs/Plan.md`に記載

## 注意事項
- ディレクトリ構成は下記の構成を遵守し基本的に変更しないこと。

## ディレクトリ構成
アプリケーションのコードに関するもののみを記載
```
.
└── app/                # FastAPIアプリケーションのソースコード
    ├── main.py         # FastAPIアプリの起動ファイル
    ├── controller.py   # main.pyで定義されたエンドポイントとserviceの処理を繋ぐファイル
    ├── models.py       # APIのデータ形式を定義 (Pydanticモデル)
    ├── services/       # 主要なGCPサービスのロジックを定義
    │   ├── gemini_service.py       # Gemini APIとの通信ロジック
    │   ├── prompt.py               # Gemini のプロンプトを定義
    │   ├── json_schema.py          # Gemini のJSONのレスポンス形式を定義
    │   └── firestore_service.py    # Firestoreの読み書きロジック
    └── static/             # フロントエンドの全コードを格納
        ├── index.html      # アプリケーションのメインHTML
        ├── script.js       # 画面操作とAPIの通信を行うJavaScript
        └── style.css       # メインHTMLのスタイルシート
```