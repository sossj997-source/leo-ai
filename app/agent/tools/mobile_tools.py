import requests

BRIDGE_URL = "https://cumulative-financial-examining-dealtime.trycloudflare.com"

def send_sms(number: str, message: str) -> str:
    """Send an SMS via the user's mobile phone"""
    try:
        res = requests.post(f"{BRIDGE_URL}/sms", json={"number": number, "message": message}, timeout=10)
        return res.text
    except Exception as e:
        return f"Bridge Error: {e}"

def open_phone_app(package_name: str) -> str:
    """Open an app on the mobile phone using its package name (e.g. com.instagram.android)"""
    try:
        res = requests.post(f"{BRIDGE_URL}/open_app", json={"package_name": package_name}, timeout=10)
        return res.text
    except Exception as e:
        return f"Bridge Error: {e}"

def get_phone_battery() -> str:
    """Check the mobile phone's battery status"""
    try:
        res = requests.get(f"{BRIDGE_URL}/battery", timeout=10)
        return res.text
    except Exception as e:
        return f"Bridge Error: {e}"


def register_mobile_tools(tool_registry):
    tool_registry.register(
        name="send_sms",
        description="Send an SMS via the user's mobile phone.",
        function=send_sms
    )
    tool_registry.register(
        name="open_phone_app",
        description="Open an app on the mobile phone using its package name.",
        function=open_phone_app
    )
    tool_registry.register(
        name="get_phone_battery",
        description="Check the mobile phone's battery status.",
        function=get_phone_battery
    )