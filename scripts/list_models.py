import os

import httpx
from dotenv import load_dotenv

load_dotenv()

response = httpx.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
    timeout=30,
)
print("Groq HTTP", response.status_code)
if response.status_code == 200:
    for model in sorted(item["id"] for item in response.json()["data"]):
        print(" ", model)
