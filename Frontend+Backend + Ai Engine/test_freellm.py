import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from ai_engine.providers.ai_provider import FreeLLMAPIProvider

async def main():
    provider = FreeLLMAPIProvider(base_url="http://localhost:3001/v1", api_key="freellmapi-4d20961b0d4f5ad146bd33b63cd54dd77c865a69506f78f7", model="gpt-oss-120b")
    result = await provider.generate_structured(prompt="What is 2+2?", response_schema={"type": "object", "properties": {"answer": {"type": "string"}}}, temperature=0.1)
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(main())
