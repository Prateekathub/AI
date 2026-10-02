from huggingface_hub import InferenceClient
import os

client = InferenceClient(
    provider="auto",
    api_key=os.getenv("HF_TOKEN")
)

response = client.chat_completion(
    model="Qwen/Qwen3-32B",
    messages=[
        {"role": "user", "content": "Say hello in one sentence."}
    ]
)

print(response.choices[0].message.content)