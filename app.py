from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from source.personal_agents import PersonalAssistantOrchestrator

app = FastAPI(title="Personal Assistant", version="1.0.0")

assistant = PersonalAssistantOrchestrator()

app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    result = await assistant.process_request(payload.message)
    return ChatResponse(response=result if isinstance(result, str) else str(result))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
