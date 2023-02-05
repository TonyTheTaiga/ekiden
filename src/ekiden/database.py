import json
from asyncio import Lock
from typing import Dict, List, Optional, Tuple

import aiofiles
from pydantic import BaseModel

from ekiden.nips import Kind, Tag

db_lock = Lock()


class Identity(BaseModel):
    name: str
    about: str
    picture: str
    pubkey: str


class DBEvent(BaseModel):
    id: str
    kind: int
    pubkey: str
    created_at: int
    tags: Tuple[Tag, ...]
    content: str
    sig: str


class Database(BaseModel):
    identities: Optional[Dict[str, Identity]] = {}
    events: Optional[Dict[str, Dict[Kind, List[DBEvent]]]] = {}

    lock: Lock = db_lock

    class Config:
        extra = "allow"
        arbitrary_types_allowed = True

    @classmethod
    async def load(cls):
        async with aiofiles.open("db.json", mode="r") as fp:
            return Database(**json.loads(await fp.read()))

    async def save_db(self):
        async with aiofiles.open("db.json", mode="w") as fp:
            await fp.write(self.json(indent=4, exclude={"lock"}))
