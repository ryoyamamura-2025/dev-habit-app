KAISUTSU_NIKI_SCHEMA = {
  "type": "object",
  "description": "構造化された回答",
  "properties": {
    "response": { "type": "string", "description": "Web検索結果を踏まえた回答" },
  },
  "required": ["response"]
}

NANASHI_MULTI_RESPONSE_SCHEMA = {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "The content of the post in 2channel style Japanese. The content must be in Japanese.",
      },
    },
    "required": ["content"],
  },
}
