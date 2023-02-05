import logging

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from tortoise import Tortoise

from ekiden.hoshi import Hoshi

logging.basicConfig(level=logging.INFO)


def create_app():
    return Starlette(
        routes=[
            WebSocketRoute(path="/", endpoint=Hoshi()),
        ],
        on_startup=[],
    )


app = create_app()
