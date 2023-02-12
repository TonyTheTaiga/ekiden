import logging

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from tortoise import Tortoise
from tortoise.functions import Count
from tortoise.transactions import atomic

from ekiden import database as db
from ekiden.hoshi import Hoshi


async def startup():
    await Tortoise.init(db_url="sqlite://ekiden.sqlite3", modules={"models": ["ekiden.database"]})
    await Tortoise.generate_schemas()


async def shutdown():
    await Tortoise.close_connections()


def create_app():
    logging.basicConfig(
        level=logging.INFO,
        format='{"name": "%(name)s", "level": "%(levelname)s", "message": %(message)s}',
    )

    return Starlette(
        routes=[
            WebSocketRoute(path="/", endpoint=Hoshi()),
        ],
        on_startup=[startup],
        on_shutdown=[shutdown],
    )


app = create_app()
