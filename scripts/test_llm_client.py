import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.llm_client import llm_client

response = llm_client.chat(
    system="You are a helpful assistant.",
    user="Say hello in exactly 5 words.",
)

print("Response:")
print(response)
