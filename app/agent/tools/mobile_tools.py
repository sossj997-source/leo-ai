import requests

BRIDGE_URL = "https://cumulative-financial-examining-dealtime.trycloudflare.com"

def register_mobile_tools(tool_registry):
    
    @tool_registry.register(name="send_sms", description="Send an SMS via the user's mobile phone")
    def send_sms(number: str, message: str) -> str:
        try:
            res = requests.post(f"{BRIDGE_URL}/sms", json={"number": number, "message": message}, timeout=10)
            return res.text
        except Exception as e:
            return f"Bridge Error: {e}"

    @tool_registry.register(name="open_phone_app", description="Open an app on the mobile phone using its package name (e.g. com.instagram.android)")
    def open_phone_app(package_name: str) -> str:
        try:
            res = requests.post(f"{BRIDGE_URL}/open_app", json={"package_name": package_name}, timeout=10)
            return res.text
        except Exception as e:
            return f"Bridge Error: {e}"

    @tool_registry.register(name="get_phone_battery", description="Check the mobile phone's battery status")
    def get_phone_battery() -> str:
        try:
            res = requests.get(f"{BRIDGE_URL}/battery", timeout=10)
            return res.text
        except Exception as e:
            return f"Bridge Error: {e}"