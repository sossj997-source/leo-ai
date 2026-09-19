from aiohttp import web
import ssl

async def index(request):
    return web.FileResponse("index.html")

app = web.Application()
app.router.add_get("/", index)
app.router.add_static("/", ".")

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain("localhost-cert.pem", "localhost-key.pem")

web.run_app(
    app,
    host="0.0.0.0",
    port=5500,
    ssl_context=ssl_context
)