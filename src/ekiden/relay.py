import json
from hashlib import sha256
from uuid import uuid4

from ekiden.database import Database, Identity
from ekiden.nips import Event, Kind, dump_json
from ekiden.subscriptions import SubscriptionPool


class AsyncRelay:
    def __init__(self, sub_pool: SubscriptionPool) -> None:
        self.conn_pool = sub_pool

    async def event(self, event_data: dict, db: Database):
        """Handles the event action.

        Args:
            event_data (dict): A dict object containing the event data.
            db (Database): The database connection.
        """
        try:
            event = Event.verify(event_data)
        except Exception as e:
            return dump_json(
                [
                    "OK",
                    dump_json(event_data).encode("utf-8") + uuid4().hex.encode("utf-8"),
                    "false",
                    "failed to verify key",
                ]
            )

        events = db.events.setdefault(event.pubkey, {})

        if event.kind == Kind.set_metadata:
            if event.kind in events:
                # A relay may delete past set_metadata events once it gets a new one for the same pubkey.
                events[event.kind].pop(0)
            await self.save_metadata(event, db=db)

        await self.conn_pool.broadcast(event)

        # Save event to db
        kind_events = events.setdefault(event.kind, [])
        kind_events.append(
            {
                "id": event.id,
                "kind": event.kind,
                "pubkey": event.pubkey,
                "created_at": event.created_at,
                "tags": event.tags,
                "content": event.content,
                "sig": event.sig,
            }
        )

        async with db.lock:
            await db.save_db()

        return dump_json(
            [
                "OK",
                sha256(event.json().encode("utf-8") + uuid4().hex.encode("utf-8")).hexdigest(),
                "true",
                "",
            ]
        )

    async def save_metadata(self, event: Event, db: Database):
        content = json.loads(event.content)
        if event.pubkey in db.identities:
            identity = db.identities.get(event.pubkey)
            print(f"updating identity {event.pubkey}:{content}")
            if "name" in content:
                identity.name = content["name"]
            if "about" in content:
                identity.about = content["about"]
            if "picture" in content:
                identity.picture = content["picture"]
        else:
            print(f"new identity {content}")
            db.identities.update(
                {
                    event.pubkey: Identity(
                        name=content["name"],
                        about=content["about"],
                        picture=content["picture"],
                        pubkey=event.pubkey,
                    )
                }
            )
