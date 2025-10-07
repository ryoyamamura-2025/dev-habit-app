import os
from google import genai
from google.genai import types

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
LOCATION = os.environ.get("LOCATION")

# Geminiクライアント初期化
_client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT_ID,
    location=LOCATION,
)

class geminiApiCaller():
    """
    Gemini API を呼び出すクラス。セーフティセッティング等は共通化する
    """
    def __init__(self, model_name, thinking_budget, response_schema=None):
        self.model_name = model_name
        self.thinking_budget = thinking_budget
        self.response_schema = response_schema

    def set_generate_content_config(self):
        base = dict(
            temperature=1, top_p=1, seed=0, max_output_tokens=65535,
            response_modalities=["TEXT"],
            safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="OFF"
                )
            ],
            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget),  # SDKに合わせる
        )
        if self.response_schema:
            base.update(response_mime_type="application/json", response_schema=self.response_schema)
        return types.GenerateContentConfig(**base)

    def text2text(self, prompt):
        print("model: ", self.model_name)
        print("thinking budget: ", self.thinking_budget)
        input_prompt = types.Part.from_text(text=prompt.strip())
        contents = [
            types.Content(
                role = "user",
                parts = [
                    input_prompt
                ]
            ),
        ]

        self.generate_content_config = self.set_generate_content_config()

        response = _client.models.generate_content(
            model = self.model_name,
            contents = contents,
            config = self.generate_content_config
        )            
        
        if self.response_schema:
            return response.parsed, response
        else:
            return response.text, response

    async def atext2text(self, prompt):
        print("model: ", self.model_name)
        print("thinking budget: ", self.thinking_budget)
        input_prompt = types.Part.from_text(text=prompt.strip())
        contents = [
            types.Content(
                role = "user",
                parts = [
                    input_prompt
                ]
            ),
        ]

        self.generate_content_config = self.set_generate_content_config()

        response = await _client.aio.models.generate_content(
            model = self.model_name,
            contents = contents,
            config = self.generate_content_config
        )            
        
        if self.response_schema:
            return response.parsed, response
        else:
            return response.text, response

        
class geminiApiCallerWithTool(geminiApiCaller):
    """
    Search Tool 付きで Gemini API を呼び出すクラス。geminiApiCallerを継承
    """
    def __init__(self, model_name, thinking_budget, response_schema=None):
        super().__init__(
            model_name = model_name, 
            thinking_budget=thinking_budget, 
            response_schema=response_schema, 
        )

    # オーバーライド
    def set_generate_content_config(self):
        # Define the grounding tool
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        base = dict(
            temperature=1, top_p=1, seed=0, max_output_tokens=65535,
            response_modalities=["TEXT"],
            safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="OFF"
                )
            ],
            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget),  # SDKに合わせる
            tools=[grounding_tool]
        )
        if self.response_schema:
            base.update(response_mime_type="application/json", response_schema=self.response_schema)
        return types.GenerateContentConfig(**base)