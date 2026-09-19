# test.py
import requests
import json
import os

BASE_URL = "http://localhost:8000"
SESSION_ID = None
CURRENT_MODE = None
ASSISTANT_NAME = "Leo"

print("="*60)
print("🤖 J.A.R.V.I.S - General & Realtime Chat")
print("="*60)
print("\nModes:")
print("  1 = General Chat (pure LLM, no web search)")
print("  2 = Realtime Chat (with Tavily search)")
print("\nCommands:")
print("  /history - See chat history")
print("  /session - Show current session ID")
print("  /sessions - List all saved sessions")
print("  /load <id> - Load a specific session")
print("  /clear - Start new session")
print("  /quit - Exit")
print("="*60)

def send_message(message: str, mode: str):
    global SESSION_ID
    endpoint = "/chat/realtime" if mode == "realtime" else "/chat"
    
    try:
        response = requests.post(
            f"{BASE_URL}{endpoint}",
            json={"message": message, "session_id": SESSION_ID}
        )
        
        if response.status_code == 200:
            data = response.json()
            SESSION_ID = data.get("session_id")
            return data.get("response", "No response")
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Connection error: {str(e)}"

def show_session_id():
    print(f"\n📋 Current Session ID: {SESSION_ID}")
    print("\n📁 Saved sessions:")
    for file in os.listdir("chats_data"):
        if file.endswith(".json"):
            print(f"  - {file}")

def load_session(session_id: str):
    global SESSION_ID
    SESSION_ID = session_id
    print(f"✅ Loaded session: {session_id}")
    print("🔍 Check memory with: 'mera naam kya hai'")

def show_sessions():
    print("\n📁 Saved Sessions:")
    for file in os.listdir("chats_data"):
        if file.endswith(".json"):
            print(f"  - {file}")

while True:
    try:
        user_input = input("\nYou: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ["/quit", "/exit"]:
            print("\nGoodbye!")
            break
        
        if user_input.startswith("/"):
            if user_input == "/history":
                if SESSION_ID:
                    response = requests.get(f"{BASE_URL}/chat/history/{SESSION_ID}")
                    if response.status_code == 200:
                        data = response.json()
                        print("\n📜 Chat History:")
                        for msg in data.get("messages", []):
                            print(f"  {msg['role']}: {msg['content']}")
                    else:
                        print("❌ Could not fetch history")
                else:
                    print("❌ No active session")
            
            elif user_input == "/clear":
                SESSION_ID = None
                print("✅ Started new session")
            
            elif user_input == "/session":
                show_session_id()
            
            elif user_input == "/sessions":
                show_sessions()
            
            elif user_input.startswith("/load "):
                session_id = user_input[6:].strip()
                load_session(session_id)
            
            else:
                print(f"❌ Unknown command: {user_input}")
            continue
        
        if not CURRENT_MODE:
            if user_input in ["1", "2"]:
                CURRENT_MODE = "general" if user_input == "1" else "realtime"
                mode_name = "General" if CURRENT_MODE == "general" else "Realtime"
                print(f"✅ Switched to {mode_name} chat")
            else:
                print("Please select mode first (1=General or 2=Realtime)")
            continue
        
        mode_label = "General" if CURRENT_MODE == "general" else "Realtime"
        response = send_message(user_input, CURRENT_MODE)
        print(f"🤖 {ASSISTANT_NAME} ({mode_label}): {response}")
    
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        break
    except Exception as e:
        print(f"❌ Error: {str(e)}")