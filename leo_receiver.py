import json
import subprocess
import time
import urllib.request

LAPTOP = "http://192.168.31.88:8000"
TOKEN = "ctIv5Xp4lEGPO-9BXDOdVqFIZ7aNr7SWYDA9i9NQNAE"
DEVICE_ID = "termux-phone"

def request(path, data=None):
    url = LAPTOP + path

    if data is not None:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-LEO-Mobile-Token": TOKEN
            }
        )
    else:
        req = urllib.request.Request(
            url,
            headers={
                "X-LEO-Mobile-Token": TOKEN
            }
        )

    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode())
    
def open_app(app):
    packages = {
        "whatsapp": "com.whatsapp",
        "youtube": "com.google.android.youtube",
        "instagram": "com.instagram.android",
    }

    package = packages.get(app.lower())

    if not package:
        return False, "Unsupported app: " + app

    result = subprocess.run(
        ["sh", "-c", f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {package}"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0 and "Error" not in result.stdout:
        return True, None

    return False, result.stderr.strip() or result.stdout.strip()
print("LEO Mobile Receiver started")
print("Device:", DEVICE_ID)

while True:
    try:
        data = request(
            "/mobile/poll?device_id=" + DEVICE_ID
        )

        command = data.get("command")

        if command:
            print("Command received:", command)

            if command.get("action") == "open_app":
                success, error = open_app(
                    command.get("app", "")
                )
            else:
                success = False
                error = "Unsupported action"

            request(
                "/mobile/ack",
                {
                    "command_id": command.get("command_id"),
                    "device_id": DEVICE_ID,
                    "success": success,
                    "error": error
                }
            )

            print(
                "Result:",
                "SUCCESS" if success else "FAILED",
                error or ""
            )

        time.sleep(1)

    except Exception as e:
        print("Receiver error:", e)
        time.sleep(3)