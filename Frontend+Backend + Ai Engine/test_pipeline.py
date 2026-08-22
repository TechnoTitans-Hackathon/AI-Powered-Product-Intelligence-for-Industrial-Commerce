import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.integration.engine_service import _build_pipeline
from backend.schemas.ai_contract import AIProcessingMode

async def main():
    print("Testing AUTO mode...")
    pipeline_auto = _build_pipeline(ai_mode=AIProcessingMode.AUTO)
    print("Agent 1:", pipeline_auto.ai_provider.get_provider_name())
    print("Agent 2:", pipeline_auto.intelligence_provider.get_provider_name())

    print("\nTesting LOCAL mode...")
    pipeline_local = _build_pipeline(ai_mode=AIProcessingMode.LOCAL)
    print("Agent 1:", pipeline_local.ai_provider.get_provider_name())
    print("Agent 2:", pipeline_local.intelligence_provider.get_provider_name())
    
    print("\nTesting FAST mode...")
    pipeline_fast = _build_pipeline(ai_mode=AIProcessingMode.FAST)
    print("Agent 1:", pipeline_fast.ai_provider.get_provider_name())
    print("Agent 2:", pipeline_fast.intelligence_provider.get_provider_name())

    print("\nTesting DEEP mode...")
    pipeline_deep = _build_pipeline(ai_mode=AIProcessingMode.DEEP)
    print("Agent 1:", pipeline_deep.ai_provider.get_provider_name())
    print("Agent 2:", pipeline_deep.intelligence_provider.get_provider_name())

if __name__ == "__main__":
    asyncio.run(main())
