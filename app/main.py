from fastapi import Request
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional
import os
import secrets
from datetime import datetime, timezone

from app.agent.models import AgentRequest
import json

from app.services.chat_service import ChatService
from app.services.groq_service import GroqService, AllGroqApisFailedError
from app.services.realtime_service import RealTimeGroqService
from app.services.writing_service import WritingService
from app.agent.tools.writing_tools import register_writing_tools
from app.services.vector_store import VectorStoreService

# Agent imports
from app.agent.agent import Agent
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.register_tools import register_basic_tools
from app.agent.proactive_manager import ProactiveManager


app = FastAPI(title="JARVIS AI")


# ==================================================
# MOBILE COMMAND SYSTEM — FOUNDATION
# ==================================================
# A dedicated token protects remote commands sent from a phone.
# Set LEO_MOBILE_TOKEN in the environment for a persistent token;
# otherwise a random token is generated for the current server run.
MOBILE_TOKEN_FILE = Path.home() / "LEO AI" / "mobile_command_token.txt"
MOBILE_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
if MOBILE_TOKEN_FILE.exists():
    MOBILE_COMMAND_TOKEN = MOBILE_TOKEN_FILE.read_text(encoding="utf-8").strip()
else:
    MOBILE_COMMAND_TOKEN = secrets.token_urlsafe(32)
    MOBILE_TOKEN_FILE.write_text(MOBILE_COMMAND_TOKEN, encoding="utf-8")
print(f"LEO MOBILE COMMAND TOKEN: {MOBILE_COMMAND_TOKEN}")


def _verify_mobile_token(token: Optional[str]) -> None:
    if not token or not secrets.compare_digest(token, MOBILE_COMMAND_TOKEN):
        raise HTTPException(401, "Invalid mobile command token.")



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://192.168.31.88:5500",
        "http://192.168.31.88:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# Lightweight phone receiver state (no Android Studio required).
MOBILE_PENDING_COMMANDS = {}
MOBILE_COMMAND_RESULTS = {}

@app.get("/health")
async def health():
    return {"status": "healthy"}


# ==================================================
# SERVICES
# ==================================================

vector_store = None
groq_service = None
realtime_service = None
chat_service = None
writing_service = None

# Agent
agent = None
tool_registry = None


try:
    # ----------------------------------------------
    # Existing services
    # ----------------------------------------------

    vector_store = VectorStoreService()

    groq_service = GroqService(
        vector_store
    )

    realtime_service = RealTimeGroqService(
        vector_store
    )

    chat_service = ChatService(
        groq_service,
        realtime_service
    )

    # ----------------------------------------------
    # Writing Service
    # ----------------------------------------------
    writing_service = WritingService(
        groq_service
    )

    # ----------------------------------------------
    # Agent services
    # ----------------------------------------------

        # ----------------------------------------------
        # ----------------------------------------------
    # Proactive services
    # ----------------------------------------------

    proactive_manager = ProactiveManager()

    # Start proactive scheduler + triggers
    proactive_manager.start()

    from app.agent.activity_monitor import ActivityMonitor

    activity_monitor = ActivityMonitor(
        engine=proactive_manager.engine,
        poll_interval=1.0,
    )

    activity_monitor.start()

    # ----------------------------------------------
    # Agent services
    # ----------------------------------------------

    tool_registry = ToolRegistry()

    register_basic_tools(
        tool_registry,
        proactive_manager=proactive_manager
    )

    agent = Agent(
        groq_service=groq_service,
        tool_registry=tool_registry
    )

    print(
        f"AGENT INITIALIZED SUCCESSFULLY "
        f"WITH {len(tool_registry)} TOOLS"
    )

        # ----------------------------------------------
    # Register Writing Tools with Agent
    # ----------------------------------------------
    register_writing_tools(
        tool_registry,
        writing_service
    )

    print("WRITING TOOLS REGISTERED SUCCESSFULLY")

    print(
        "ALL SERVICES INITIALIZED SUCCESSFULLY"
    )
except Exception as e:

    print(
        f"CRITICAL ERROR INITIALIZING SERVICES: "
        f"{repr(e)}"
    )


# ==================================================
# REQUEST MODEL
# ==================================================

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class MobileCommandRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    device_id: Optional[str] = None


# ==================================================
# MOBILE COMMAND
# ==================================================

@app.get("/mobile/status")
async def mobile_status(x_leo_mobile_token: Optional[str] = Header(default=None)):
    _verify_mobile_token(x_leo_mobile_token)
    return {
        "status": "ready",
        "agent": agent is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/mobile/command")
async def mobile_command(
    req: MobileCommandRequest,
    x_leo_mobile_token: Optional[str] = Header(default=None),
):
    _verify_mobile_token(x_leo_mobile_token)

    if agent is None:
        raise HTTPException(503, "Agent is not initialized.")

    if not req.message.strip():
        raise HTTPException(400, "Command cannot be empty.")

    try:
        result = agent.run(
            message=req.message.strip(),
            session_id=req.session_id,
        )

        return {
            "success": result.success,
            "message": result.message,
            "session_id": req.session_id,
            "device_id": req.device_id,
            "source": "mobile",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "plan": result.plan.model_dump() if result.plan else None,
            "tool_calls": [x.model_dump() for x in result.tool_calls],
            "tool_results": [x.model_dump() for x in result.tool_results],
        }

    except Exception as e:
        raise HTTPException(400, str(e))


# ==================================================
# NORMAL CHAT
# ==================================================

@app.post("/chat")
async def chat(req: ChatRequest):

    if chat_service is None:
        raise HTTPException(
            status_code=503,
            detail="Chat service is not initialized."
        )

    try:

        session_id = (
            chat_service.get_or_create_session(
                req.session_id
            )
        )

        response = (
            chat_service.process_message(
                session_id,
                req.message
            )
        )

        return {
            "session_id": session_id,
            "response": response
        }

    except AllGroqApisFailedError:

        raise HTTPException(
            status_code=503,
            detail="AI services unavailable."
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ==================================================
# REALTIME CHAT
# ==================================================

@app.post("/chat/realtime")
async def chat_realtime(req: ChatRequest):

    if chat_service is None:
        raise HTTPException(
            status_code=503,
            detail="Chat service is not initialized."
        )

    try:

        session_id = (
            chat_service.get_or_create_session(
                req.session_id
            )
        )

        response = (
            chat_service.process_realtime_message(
                session_id,
                req.message
            )
        )

        return {
            "session_id": session_id,
            "response": response
        }

    except AllGroqApisFailedError:

        raise HTTPException(
            status_code=503,
            detail="AI services unavailable."
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ==================================================
# CHAT STREAM
# ==================================================

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):

    if chat_service is None:
        raise HTTPException(
            status_code=503,
            detail="Chat service is not initialized."
        )

    try:

        session_id = (
            chat_service.get_or_create_session(
                req.session_id
            )
        )

        generator = (
            chat_service.process_message_stream(
                session_id,
                req.message
            )
        )

        def event_stream():

            yield (
                f"data: "
                f"{json.dumps({'session_id': session_id})}"
                f"\n\n"
            )

            try:

                for chunk in generator:

                    if chunk:

                        yield (
                            f"data: "
                            f"{json.dumps({'chunk': chunk})}"
                            f"\n\n"
                        )

                yield (
                    f"data: "
                    f"{json.dumps({'done': True})}"
                    f"\n\n"
                )

            except Exception as e:

                yield (
                    f"data: "
                    f"{json.dumps({'error': str(e)})}"
                    f"\n\n"
                )

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ==================================================
# REALTIME STREAM
# ==================================================

@app.post("/chat/realtime/stream")
async def chat_realtime_stream(
    req: ChatRequest
):

    if chat_service is None:
        raise HTTPException(
            status_code=503,
            detail="Chat service is not initialized."
        )

    try:

        session_id = (
            chat_service.get_or_create_session(
                req.session_id
            )
        )

        generator = (
            chat_service
            .process_realtime_message_stream(
                session_id,
                req.message
            )
        )

        def event_stream():

            yield (
                f"data: "
                f"{json.dumps({'session_id': session_id})}"
                f"\n\n"
            )

            try:

                for item in generator:

                    if isinstance(item, dict):

                        yield (
                            f"data: "
                            f"{json.dumps(item)}"
                            f"\n\n"
                        )

                    elif item:

                        yield (
                            f"data: "
                            f"{json.dumps({'chunk': item})}"
                            f"\n\n"
                        )

                yield (
                    f"data: "
                    f"{json.dumps({'done': True})}"
                    f"\n\n"
                )

            except Exception as e:

                yield (
                    f"data: "
                    f"{json.dumps({'error': str(e)})}"
                    f"\n\n"
                )

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ==================================================
# LEO AGENT
# ==================================================

@app.post("/agent")
async def run_agent(req: ChatRequest):

    if agent is None:

        raise HTTPException(
            status_code=503,
            detail="Agent is not initialized."
        )

    try:

        result = agent.run(
            message=req.message,
            session_id=req.session_id
        )

        return result.model_dump()

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
    # ==================================================
# WRITING ENDPOINTS
# ==================================================

class WritingRequest(BaseModel):
    type: str          # email, report, blog, letter, summary, improve
    topic: str = ""
    content: str = ""
    recipient: str = "Sir"
    tone: str = "professional"
    length: str = "medium"
    word_count: int = 500


@app.post("/writing/generate")
async def generate_writing(req: WritingRequest):
    """Generate writing content (email, report, blog, letter, summary, improve)"""
    if writing_service is None:
        raise HTTPException(
            status_code=503,
            detail="Writing service not initialized."
        )

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
            raise HTTPException(
                status_code=400,
                detail="Unknown writing type. Use: email, report, blog, letter, summary, improve"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/writing/list")
async def list_writing():
    """List all saved writing outputs"""
    if writing_service is None:
        raise HTTPException(status_code=503, detail="Writing service not initialized.")
    return {"files": writing_service.list_outputs()}


@app.get("/writing/read/{filename}")
async def read_writing(filename: str):
    """Read a saved writing output"""
    if writing_service is None:
        raise HTTPException(status_code=503, detail="Writing service not initialized.")
    content = writing_service.read_output(filename)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"filename": filename, "content": content}
from fastapi.responses import HTMLResponse

@app.get("/mobile/pair", response_class=HTMLResponse)
async def mobile_pair_page():
    return HTMLResponse("""
<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LEO Mobile</title>
<style>
body{margin:0;background:#090713;color:#eee;font-family:Arial,sans-serif;min-height:100vh;display:grid;place-items:center}
.card{width:min(92vw,520px);padding:24px;border:1px solid #3a2b58;border-radius:22px;background:#141020;box-shadow:0 0 40px #000}
input,button{width:100%;box-sizing:border-box;padding:14px;margin-top:10px;border-radius:12px;border:1px solid #44345f;background:#0d0a16;color:#fff}
button{cursor:pointer;background:#27154a}.muted{color:#aaa;font-size:14px}.ok{color:#7cffb2}.err{color:#ff7c9c}
</style></head><body><div class="card">
<h1>LEO Mobile</h1><p class="muted">Enter the token shown in the laptop terminal.</p>
<input id="token" type="password" placeholder="Mobile command token">
<button onclick="pair()">Pair this phone</button>
<hr style="border-color:#2b213d;margin:20px 0">
<input id="cmd" placeholder="e.g. open Chrome">
<button onclick="send()">Send laptop command</button><p id="out" class="muted"></p>
</div><script>
const out=document.getElementById('out');
async function pair(){
  const t=document.getElementById('token').value.trim();
  if(!t){out.textContent='Enter token';out.className='err';return}
  try{
    const r=await fetch('/mobile/pair',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token:t})});
    const d=await r.json();
    if(!r.ok) throw Error(d.detail||('HTTP '+r.status));
    localStorage.setItem('leo_mobile_paired','1');
    out.textContent='Phone paired successfully. Open the receiver page.';
    out.className='ok';
  }catch(e){out.textContent=e.message;out.className='err'}
}
async function send(){
  const c=document.getElementById('cmd').value.trim();
  if(!c){out.textContent='Enter a command';out.className='err';return}
  try{
    const r=await fetch('/mobile/command',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:c})});
    const d=await r.json();
    if(!r.ok) throw Error(d.detail||('HTTP '+r.status));
    out.textContent=d.message||'Command completed.';out.className=d.success?'ok':'err';
  }catch(e){out.textContent=e.message;out.className='err'}
}
</script></body></html>
""")

@app.post("/mobile/pair")
async def mobile_pair(req: dict, response: Response):
    if req.get("token") != MOBILE_COMMAND_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid mobile command token")
    response.set_cookie(
        key="leo_mobile_session",
        value=MOBILE_COMMAND_TOKEN,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60*60*24*30,
    )
    return {"success": True, "paired": True}


@app.get("/mobile/receiver", response_class=HTMLResponse)
async def mobile_receiver_page():
    return HTMLResponse("""
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LEO Mobile Receiver</title>
<style>
body{margin:0;background:#080711;color:#eee;font-family:Arial,sans-serif;min-height:100vh;display:grid;place-items:center}
.card{width:min(92vw,520px);padding:24px;border:1px solid #3a2b58;border-radius:22px;background:#141020;box-shadow:0 0 40px #000}
h1{margin:0 0 8px}.muted{color:#aaa;font-size:14px}.ok{color:#7cffb2}.err{color:#ff7c9c}
</style></head><body><div class="card">
<h1>LEO Mobile Receiver</h1><p id="status" class="muted">Connecting…</p>
<p class="muted">Keep this page open on your phone.</p>
</div><script>
const deviceId=localStorage.getItem('leo_device_id')||('android-'+Math.random().toString(36).slice(2));
localStorage.setItem('leo_device_id',deviceId);
const s=document.getElementById('status');
async function poll(){
 try{
  const r=await fetch('/mobile/poll?device_id='+encodeURIComponent(deviceId),{credentials:'same-origin'});
  if(!r.ok) throw Error('Receiver HTTP '+r.status);
  const d=await r.json();
  s.textContent='Connected • waiting for commands';s.className='ok';
  if(d.command) await execute(d.command);
 }catch(e){s.textContent='Receiver connection error: '+e.message;s.className='err';}
}
async function execute(cmd){
 let ok=false,error='';
 try{
  if(cmd.action==='open_app' && cmd.app==='whatsapp'){
    location.href='intent://send/#Intent;scheme=whatsapp;package=com.whatsapp;end'; ok=true;
  }else if(cmd.action==='open_app' && cmd.app==='youtube'){
    location.href='intent://www.youtube.com/#Intent;scheme=https;package=com.google.android.youtube;end'; ok=true;
  }else if(cmd.action==='open_url'){location.href=cmd.url;ok=true;}
  else error='Unsupported mobile action: '+cmd.action;
 }catch(e){error=e.message}
 fetch('/mobile/ack',{method:'POST',headers:{'Content-Type':'application/json'},
  credentials:'same-origin',body:JSON.stringify({command_id:cmd.command_id,device_id:deviceId,success:ok,error:error})}).catch(()=>{});
}
poll();setInterval(poll,1500);
</script></body></html>
""")

@app.get("/mobile/poll")
async def mobile_poll(device_id: str, request: Request):
    token = request.headers.get("X-LEO-Mobile-Token") or request.cookies.get("leo_mobile_session")
    if token != MOBILE_COMMAND_TOKEN:
        raise HTTPException(status_code=401, detail="Mobile phone is not paired")
    command = MOBILE_PENDING_COMMANDS.pop(device_id, None)
    return {"success": True, "command": command}


@app.post("/mobile/send")
async def mobile_send_command(req: dict, request: Request):
    """Queue a phone action from the laptop-side LEO client."""
    # Reuse the same token guard used by /mobile/command when available.
    token = request.headers.get("X-LEO-Mobile-Token")
    if token != MOBILE_COMMAND_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid mobile command token")
    action = req.get("action")
    device_id = req.get("device_id", "default")
    if action not in {"open_app", "open_url"}:
        raise HTTPException(status_code=400, detail="Unsupported mobile action")
    command_id = str(uuid.uuid4())
    MOBILE_PENDING_COMMANDS[device_id] = {
        "command_id": command_id,
        "action": action,
        "app": req.get("app"),
        "url": req.get("url"),
        "created_at": time.time()
    }
    return {"success": True, "command_id": command_id, "queued": True}

@app.get("/mobile/poll")
async def mobile_poll(device_id: str, request: Request):
    token = request.headers.get("X-LEO-Mobile-Token")
    if token != MOBILE_COMMAND_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid mobile command token")
    command = MOBILE_PENDING_COMMANDS.pop(device_id, None)
    return {"success": True, "command": command}

@app.post("/mobile/ack")
async def mobile_ack(req: dict, request: Request):
    token = request.headers.get("X-LEO-Mobile-Token") or request.cookies.get("leo_mobile_session")
    if token != MOBILE_COMMAND_TOKEN:
        raise HTTPException(status_code=401, detail="Mobile phone is not paired")
    MOBILE_COMMAND_RESULTS[req.get("command_id", str(uuid.uuid4()))] = req
    return {"success": True}
