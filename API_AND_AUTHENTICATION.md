# API and Authentication

## FreeLLMAPI Proxy Gateway
This project utilizes a local gateway proxy (`freellmapi`) to orchestrate OpenAI-compatible calls to advanced models (`gpt-oss-120b`). 
- **Endpoint**: `http://localhost:3001/v1`
- **Authentication**: Handled transparently by the proxy runtime. 
- **Secret Management**: No hardcoded API keys exist in the UniHack codebase. The `.env` file uses a blank or local `FREELLMAPI_API_KEY` to route requests exclusively to the local gateway proxy.

## FastAPI Backend
The backend runs locally on port `8000`. By default, no restrictive CORS policies or JWT authentication are enforced on the API since it is meant for local evaluation during the hackathon.
