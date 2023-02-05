import logging

from starlette.websockets import WebSocket, WebSocketDisconnect

from ekiden import database
from ekiden.nips import Filters
from ekiden.relay import AsyncRelay
from ekiden.subscriptions import Subscription, SubscriptionPool

logging.basicConfig(level=logging.INFO)


class Hoshi:
    sub_pool = SubscriptionPool()
    relay = AsyncRelay(sub_pool=sub_pool)

    async def __call__(self, scope, receive, send):
        websocket = WebSocket(scope=scope, receive=receive, send=send)
        await self.endpoint(websocket)

    async def endpoint(self, websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                msg = await websocket.receive_json()
                if msg[0] == "EVENT":
                    """
                    used to publish events
                    """
                    response = await self.relay.event(msg[1])
                    await websocket.send_text(response)
                elif msg[0] == "REQ":
                    """
                    used to request events and subscribe to new updates
                    """
                    sub = Subscription(
                        filters=Filters.parse_obj(msg[2]),
                        websocket=websocket,
                        subscription_id=msg[1],
                    )
                    await self.sub_pool.add_subscription(subscription=sub)
                    for event in await database.Event.all():
                        await sub.send(event.nipple())

                elif msg[0] == "CLOSE":
                    """
                    used to stop previous subscriptions
                    """
                    await self.handle_disconnect(websocket)

        except WebSocketDisconnect:
            await self.handle_disconnect(websocket)

    async def handle_disconnect(self, websocket: WebSocket):
        subscription = await self.sub_pool.get_subscription(websocket=websocket)
        if subscription:
            await self.sub_pool.remove_subscription(subscription)
