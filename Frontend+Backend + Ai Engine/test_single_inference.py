import sys
import os
import asyncio
from dotenv import load_dotenv

workspace_root = r"D:\Hackathon\Frontend+Backend + Ai Engine"
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)
load_dotenv(os.path.join(workspace_root, ".env"))

from backend.integration.engine_service import integrated_ai_service
from backend.schemas.ai_contract import AIProcessingMode
from ai_engine.schemas import ProductInput

def test_single_inference():
    product_input = ProductInput(
        mfg_part_number="TEST-1234",
        part_description="This is a test resistor, 10 ohm, 5% tolerance.",
        brand="Vishay",
        manufacturer="Vishay",
        category="Resistor",
    )
    
    print("Running process_intelligence with FAST mode (Agent 1 + Agent 2 = FreeLLMAPI/GPT-OSS)...")
    # This will trigger the full pipeline with FreeLLMAPI
    pipeline_result = integrated_ai_service.process_intelligence(
        product_input=product_input,
        pre_retrieved_evidence=[],
        ai_mode=AIProcessingMode.FAST
    )
    
    print(f"Success: {pipeline_result.success}")
    if pipeline_result.intelligence:
        print(f"Processing Status: {pipeline_result.intelligence.processing_status}")
    else:
        print("Intelligence is None")
        
    print("Errors:")
    for e in pipeline_result.errors:
        print(f" - {e.stage}: {e.message}")
        
    print("Diagnostics:")
    for k, v in pipeline_result.diagnostics.items():
        print(f"  {k}: {v}")
        
if __name__ == "__main__":
    test_single_inference()
