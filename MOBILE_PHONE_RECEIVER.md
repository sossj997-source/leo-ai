# LEO Phone Receiver v4

1. Start backend: `python run.py`.
2. Phone: open `http://<LAPTOP_IP>:8000/mobile/pair`.
3. Enter the token and tap **Pair this phone**. The server sets a secure session cookie.
4. Open `http://<LAPTOP_IP>:8000/mobile/receiver` in the same browser.
5. Receiver should show **Connected • waiting for commands**.
6. Laptop can queue `open_app` actions at `/mobile/send`.
7. Receiver polls every 1.5 seconds and launches supported apps using Android intents.

This avoids storing the secret token in JavaScript/localStorage. Keep the phone and laptop on the trusted LAN and do not expose port 8000 publicly.
