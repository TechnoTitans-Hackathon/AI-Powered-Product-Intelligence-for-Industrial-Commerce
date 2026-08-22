# Environment Variables Setup

The configuration for the core application is located in `.env` within the `Frontend+Backend + Ai Engine` folder.

> [!IMPORTANT]
> The `.env.example` provides all required structure. Do not commit actual `.env` files into source control.

## Required Variables

### AI Gateway
```env
FREELLMAPI_BASE_URL=http://localhost:3001/v1
FREELLMAPI_API_KEY= # Can be empty, strictly local evaluation via proxy
FREELLMAPI_MODEL_AGENT1=gpt-oss-120b
FREELLMAPI_MODEL_AGENT2=gpt-oss-120b
```

### Local Fallback
```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:9b-q4_K_M
OLLAMA_TIMEOUT=180
```

### Database & Storage
```env
DATABASE_URL="sqlite:///./product_intelligence.db"
STORAGE_BASE_PATH="./data_storage"
VECTOR_STORE_PATH="./data_storage/vector_store"
```
