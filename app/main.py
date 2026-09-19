# app/main.py
from fastapi import Request
import time
import uuid
import logging
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional
import os
import secrets
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import asyncio
import json

logger = logging.getLogger("J.A.R.V.I.S")

# Global service references
vector_store = None
groq_service = None
realtime_service = None
chat_service = None
writing_service = None
agent = None
tool_registry = None
telegram_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store, groq_service, realtime_service, chat_service, writing_service, agent, tool_registry, telegram_task
    
    print("=" * 60)
    print("J.A.R.V.I.S - Starting Up...")
    print("=" * 60)
    
    try:
        from app.services.vector_store import VectorStoreService
        print("Initializing vector store service...")
        vector_store = VectorStoreService()
        print("Vector store initialized successfully")
        
        from app.services.groq_service import GroqService
        print("Initializing Groq service...")
        groq_service = GroqService(vector_store)
        print("Groq service initialized successfully")
        
        from app.services.realtime_service import RealTimeGroqService
        print("Initializing Realtime Groq service...")
        realtime_service = RealTimeGroqService(vector_store)
        print("Realtime Groq service initialized successfully")
        
        from app.services.chat_service import ChatService
        print("Initializing ChatService...")
        chat_service = ChatService(groq_service, realtime_service)
        print("Chat service initialized successfully")
        
        from app.services.writing_service import WritingService
        from app.agent.tools.writing_tools import register_writing_tools
        print("Initializing WritingService...")
        writing_service = WritingService(groq_service)
        print("WritingService initialized successfully")
        
        from app.agent.agent import Agent
        from app.agent.tool_registry import ToolRegistry
        from app.agent.tools.register_tools import register_basic_tools
        from app.agent.proactive_manager import ProactiveManager
        
        print("Initializing ProactiveManager...")
        proactive_manager = ProactiveManager()
        proactive_manager.start()
        
        from app.agent.activity_monitor import ActivityMonitor
        activity_monitor = ActivityMonitor(
            engine=proactive_manager.engine,
            poll_interval=1.0,
        )
        activity_monitor.start()
        
        print("Initializing tool registry...")
        tool_registry = ToolRegistry()
        register_basic_tools(tool_registry, proactive_manager=proactive_manager)
        
        print("Initializing Agent...")
        agent = Agent(groq_service=groq_service, tool_registry=tool_registry)
        print(f"AGENT INITIALIZED SUCCESSFULLY WITH {len(tool_registry)} TOOLS")
        
        register_writing_tools(tool_registry, writing_service)
        print("WRITING TOOLS REGISTERED SUCCESSFULLY")
        
        # Start Telegram Bot
        try:
            from app.telegram_bot import start_telegram_bot
            from config import TELEGRAM_BOT_TOKEN
            
            if TELEGRAM_BOT_TOKEN:
                telegram_app = start_telegram_bot()
                if telegram_app:
                    await telegram_app.initialize()
                    await telegram_app.start()
                    telegram_task = asyncio.create_task(
                        telegram_app.updater.start_polling()
                    )
                    print("TELEGRAM BOT STARTED SUCCESSFULLY")
                else:
                    print("TELEGRAM BOT NOT STARTED (init failed)")
            else:
                print("TELEGRAM BOT NOT STARTED (token missing)")
        except Exception as e:
            print(f"TELEGRAM BOT ERROR: {e}")
        
        print("=" * 60)
        print("ALL SERVICES INITIALIZED SUCCESSFULLY")
        print("=" * 60)
        
        yield
        
        print("Shutting down J.A.R.V.I.S...")
        if telegram_task:
            telegram_task.cancel()
            try:
                await telegram_task
            except asyncio.CancelledError:
                pass
            print("Telegram bot stopped")
        
    except Exception as e:
        print(f"CRITICAL ERROR INITIALIZING SERVICES: {repr(e)}")
        raise


app = FastAPI(title="JARVIS AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# HEALTH
# ==================================================
@app.get("/health")
async def health():
    return {"status": "healthy"}


# ==================================================
# REQUEST MODELS
# ==================================================
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class WritingRequest(BaseModel):
    type: str
    topic: str = ""
    content: str = ""
    recipient: str = "Sir"
    tone: str = "professional"
    length: str = "medium"
    word_count: int = 500


# ==================================================
# CHAT
# ==================================================
@app.post("/chat")
async def chat(req: ChatRequest):
    if chat_service is None:
        raise HTTPException(status_code=503, detail="Chat service not initialized.")
    try:
        session_id = chat_service.get_or_create_session(req.session_id)
        response = chat_service.process_message(session_id, req.message)
        return {"session_id": session_id, "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================================================
# REALTIME CHAT
# ==================================================
@app.post("/chat/realtime")
async def chat_realtime(req: ChatRequest):
    if chat_service is None:
        raise HTTPException(status_code=503, detail="Chat service not initialized.")
    try:
        session_id = chat_service.get_or_create_session(req.session_id)
        response = chat_service.process_realtime_message(session_id, req.message)
        return {"session_id": session_id, "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================================================
# AGENT
# ==================================================
@app.post("/agent")
async def run_agent(req: ChatRequest):
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized.")
    try:
        result = agent.run(message=req.message, session_id=req.session_id)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================================================
# WRITING
# ==================================================
@app.post("/writing/generate")
async def generate_writing(req: WritingRequest):
    if writing_service is None:
        raise HTTPException(status_code=503, detail="Writing service not ready")
    try:
        if req.type == "email":
            result = writing_service.write_email(req.topic, req.recipient, req.tone)
        elif req.type == "report":
            result = writing_service.write_report(req.topic, req.content, req.length)
        elif req.type == "blog":
            result = writing_service.write_blog(req.topic, req.tone, req.word_count)
        elif req.type == "letter":
            result = writing_service.write_letter(req.topic, req.recipient, req.tone)
        elif req.type == "summary":
            result = writing_service.write_summary(req.content, req.length)
        elif req.type == "improve":
            result = writing_service.improve_text(req.content, req.tone)
        else:
            raise HTTPException(status_code=400, detail="Unknown writing type")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/writing/list")
async def list_writing():
    if writing_service is None:
        raise HTTPException(status_code=503, detail="Writing service not ready")
    return {"files": writing_service.list_outputs()}


# ==================================================
# RUN
# ==================================================
def run():
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()