from http import HTTPStatus

from aiohttp import web
from botbuilder.core.integration import aiohttp_error_middleware

from botbuilder.schema import Activity
from handler import adapter, bot_app
from config import Config



routes = web.RouteTableDef()

@routes.post("/api/messages")
async def on_messages(req: web.Request) -> web.Response:
    body = await req.json()
    activity = Activity().deserialize(body)

    auth_header = req.headers.get("Authorization", "")

    # Use adapter to handle activity and call bot
    await adapter.process_activity(activity, auth_header, bot_app.on_turn)
    return web.Response(status=HTTPStatus.OK)

app = web.Application(middlewares=[aiohttp_error_middleware])
app.add_routes(routes)
app.router.add_static("/charts/", path="/src/charts", show_index=True)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=Config.PORT)