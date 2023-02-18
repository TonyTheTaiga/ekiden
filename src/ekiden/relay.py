from hashlib import sha256
from uuid import uuid4

from tortoise.exceptions import DoesNotExist
from tortoise.transactions import atomic

from ekiden import database, logger
from ekiden.nips import ETag, Event, Kind, dump_json
from ekiden.subscriptions import SubscriptionPool


class AsyncRelay:
    def __init__(self, sub_pool: SubscriptionPool) -> None:
        self.conn_pool = sub_pool

    @atomic()
    async def event(self, event_data: dict):
        """Handles the event action.

        Args:
            event_data (dict): A dict object containing the event data.
            db (Database): The database connection.
        """
        try:
            event = Event.verify(event_data)
        except:
            return dump_json(
                [
                    "OK",
                    dump_json(event_data).encode("utf-8") + uuid4().hex.encode("utf-8"),
                    "false",
                    "failed to verify key",
                ]
            )

        await self.conn_pool.broadcast(event)

        match event.kind:
            case Kind.set_metadata:
                await self.delete_event(event)
            case Kind.contact_list:
                await self.delete_event(event)
            case Kind.delete:
                for tag in event.tags:
                    if not isinstance(tag, ETag):
                        continue
                    await database.Event.filter(id=tag.id).delete()

        await database.Event.create(
            id=event.id,
            kind=event.kind,
            content=event.content,
            created_at=event.created_at,
            tags=[tag.dict() for tag in event.tags],
            pubkey=event.pubkey,
            sig=event.sig,
        )

        return dump_json(
            [
                "OK",
                sha256(event.json().encode("utf-8") + uuid4().hex.encode("utf-8")).hexdigest(),
                "true",
                "",
            ]
        )

    async def delete_event(self, event):
        try:
            if db_event := await database.Event.get(pubkey=event.pubkey, kind=event.kind):
                await db_event.delete()
        except DoesNotExist:
            pass
