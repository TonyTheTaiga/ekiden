import json
import logging

from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from ekiden.subscriptions import Subscription, SubscriptionPool
from ekiden.database import Database
from ekiden.nips import Event, Filters
from ekiden.relay import AsyncRelay

logging.basicConfig(level=logging.INFO)


class RelayEndpoint:
    sub_pool = SubscriptionPool()
    relay = AsyncRelay(sub_pool=sub_pool)

    async def __call__(self, scope, receive, send):
        websocket = WebSocket(scope=scope, receive=receive, send=send)
        await self.endpoint(websocket)

    async def endpoint(self, websocket: WebSocket):
        await websocket.accept()
        db = await Database.load()
        try:
            while True:
                msg = await websocket.receive_text()
                decoded = json.loads(msg)
                if decoded[0] == "EVENT":
                    """
                    used to publish events
                    """
                    response = await self.relay.event(decoded[1], db)
                    await websocket.send_text(response)
                elif decoded[0] == "REQ":
                    """
                    used to request events and subscribe to new updates
                    """
                    self.sub_pool.add_subscription(
                        subscription=Subscription(
                            filters=Filters.parse_obj(decoded[2]),
                            websocket=websocket,
                            subscription_id=decoded[1],
                        )
                    )
                elif decoded[0] == "CLOSE":
                    """
                    used to stop previous subscriptions
                    """
                    subscription = self.sub_pool.get_subscription(websocket=websocket)
                    self.sub_pool.remove_subscription(subscription)

        except WebSocketDisconnect:
            self.handle_disconnect(websocket)

    def handle_disconnect(self, websocket: WebSocket):
        subscription = self.sub_pool.get_subscription(websocket=websocket)
        if subscription:
            self.sub_pool.remove_subscription(subscription)


def create_app():
    return Starlette(routes=[WebSocketRoute(path="/", endpoint=RelayEndpoint())])


app = create_app()
