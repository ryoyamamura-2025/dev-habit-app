from google.genai import types

KAISUTSU_NIKI_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        'summary': types.Schema(type=types.Type.STRING),
        'reference_url': types.Schema(type=types.Type.STRING),
    },
    required=['summary', 'reference_url']
)
