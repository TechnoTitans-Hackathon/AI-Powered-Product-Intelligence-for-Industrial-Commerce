import asyncio
from ai_engine.providers.ai_provider import OllamaProvider

async def main():
    provider = OllamaProvider()
    
    prompt = """Evaluate if deep reasoning (Agent 2) is required.

Known Info:
[{'field': 'manufacturer', 'value': 'Eaton Corporation'}]

Missing Info required:
['Maximum Operating Pressure (PSI/Bar)', 'Maximum Flow Rate (GPM/LPM)']

Evidence Gathered:
['ID: RESEARCH_PROVIDER_UNAVAILABLE | Source: unknown_source | Content: RESEARCH_PROVIDER_UNAVAILABLE...']

Decide if the evidence needs complex extraction, conflict resolution, or synthesis (Agent 2 required), or if the known information is already sufficient and evidence is straightforward (Agent 2 NOT required).

Respond with strictly valid JSON matching:
{
  "agent2_required": true or false,
  "reason": "explanation",
  "task": {
    "objective": "what Agent 2 should focus on, if required",
    "evidence_ids": ["ids of relevant evidence"]
  }
}"""
    
    system = "You are a routing layer. Decide if deep reasoning is needed based on evidence."
    
    try:
        print("Testing with format=json...")
        res = await provider.generate_structured(prompt, system, temperature=0.1)
        print("Success:", res)
    except Exception as e:
        print("Failure:", e)

if __name__ == "__main__":
    asyncio.run(main())
