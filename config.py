import os
from dotenv import load_dotenv

load_dotenv()

# .envファイルからGemini APIキーを読み込む
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# APIキーが設定されていない場合の警告
if not GEMINI_API_KEY:
    print("警告: .envファイルにGEMINI_API_KEYが設定されていません。")
    print("Gemini APIを使用するには、有効なキーを設定してください。")