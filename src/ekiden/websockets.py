"""
Defines a handler that can be used with the websockets library to build a server.
"""
import json
from typing import List

import aiofiles
from pydantic import BaseModel
from websockets.server import WebSocketServerProtocol

from ekiden.database import Database, Identity
from ekiden.nips import Event, Filters, Kind, Tag, dump_json
from ekiden.relay import AsyncRelay

relay = AsyncRelay()


subscriptions = []


def validate_ids(candidates, subject):
    if len(candidates) == 0:
        return True

    return True if subject in candidates else False


def validate_authors(candidates, subject):
    if len(candidates) == 0:
        return True

    return True if subject in candidates else False


def validate_filters(event: Event, filters: Filters):
    if validate_ids(filters.ids, event.id) and validate_authors(
        filters.authors, event.pubkey
    ):
        return True
    return False


async def publication_handler(websocket, db: Database, event: Event):
    # Publishe the event to all valid subscriptions
    for websocket, subscription_id, filters in subscriptions:
        if websocket.open:
            if validate_filters(event, filters):
                await websocket.send(
                    dump_json(["EVENT", subscription_id, event.dict()])
                )
        else:
            # remove from list of subscriptions
            pass


async def subscription_handler(
    websocket: WebSocketServerProtocol,
    db: Database,
    subscription_id: str,
    filters: Filters,
):
    subscriptions.append((websocket, subscription_id, filters))

    # send old messages
    hits = []
    for user_pubkey, user_events in db.events.items():
        for kind, kind_events in user_events.items():
            for event in kind_events:
                if validate_filters(event, filters):
                    hits.append(event)

    for event in hits:
        await websocket.send(dump_json(["EVENT", subscription_id, event.dict()]))


class Subscriber:
    def __init__(
        self, websocket: WebSocketServerProtocol, subscription_id: str, filters: Filters
    ):
        self.websocket = websocket
        self.subscription_id = subscription_id
        self.filters = filters


class Server:
    def __init__(self):
        self.subscriptions: List[Subscriber] = []

    async def handler(self, websocket: WebSocketServerProtocol):
        """Main handler to handle client connections.
        Args:
            websocket (WebSocketServerProtocol): Object that represents a websocket server connection.
        """
        db = await Database.load()

        async for message in websocket:
            decoded = json.loads(message)
            if decoded[0] == "EVENT":
                response = await relay.event(decoded[1], db)
                await websocket.send(response)

            elif decoded[0] == "REQ":
                subscription_id = decoded[1]
                filters = Filters.parse_obj(decoded[2])
                self.subscriptions.append(
                    Subscriber(
                        websocket, subscription_id=subscription_id, filters=filters
                    )
                )
                # await relay.handle_request(subscription_id, filters, db)

            # elif decoded[0] == "CLOSE":
            #     pass

    async def broadcast(self):
        pass
