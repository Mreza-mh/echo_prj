#!/usr/bin/env python
"""تست سریع اتصال به Arvan API"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# بارگذاری .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

api_base = os.getenv("ARVAN_AI_BASE_URL")
model = os.getenv("ARVAN_AI_MODEL")

print("=" * 70)
print("🧪 تست اتصال به Arvan Cloud AI")
print("=" * 70)
print(f"URL: {api_base[:80]}...")
print(f"Model: {model}")
print()

payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": "سلام! لطفاً یک جمله کوتاه به فارسی بنویس"
        }
    ],
    "temperature": 0.7,
    "max_tokens": 50
}

print("📤 ارسال درخواست...")

try:
    # ارسال با header Authorization
    response = requests.post(
        api_base,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('ARVAN_AI_API_KEY')}"
        },
        json=payload,
        timeout=30
    )
    
    print(f"📥 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"✅ پاسخ دریافت شد:")
        print(f"   {content}")
    else:
        print(f"❌ خطا:")
        print(f"   {response.text}")
        
except Exception as e:
    print(f"❌ خطا در اتصال: {e}")

print("=" * 70)
