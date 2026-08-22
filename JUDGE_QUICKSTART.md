# Judge Quickstart

Follow these steps to fully evaluate the UniHack Product Intelligence Platform locally.

## 1. Start the FreeLLMAPI Proxy
1. Open a terminal and navigate to `freellmapi/`.
2. Run `npm install` and then `npm run dev` to start the local proxy on port 3001.

## 2. Start the Backend API
1. Navigate to `Frontend+Backend + Ai Engine/`.
2. Ensure you have activated your Python virtual environment.
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and ensure `FREELLMAPI_BASE_URL` points to `http://localhost:3001/v1`.
5. Start the backend: `python -m uvicorn backend.main:app --reload` (Runs on port 8000).

## 3. Start the Frontend
1. Open a new terminal and navigate to `Frontend+Backend + Ai Engine/frontend/`.
2. Run `npm install`.
3. Start the Vite server: `npm run dev`.

## 4. Evaluation
You can now upload a sample PDF (such as the Pico Datasheet found in `Frontend+Backend + Ai Engine/data_storage/validation/`) or enter a supplier URL in the frontend to witness the AI Agent dynamically structuring the parameters.
