import logging
from typing import MutableSet, Optional

from starlette.websockets import WebSocket

from ekiden.nips import Event, Filters, dump_json

logger = logging.getLogger(__name__)


def validate_ids(candidates, subject):
    if len(candidates) == 0:
        return True

    return True if subject in candidates else False


def validate_authors(candidates, subject):
    if len(candidates) == 0:
        return True

    return True if subject in candidates else False


def validate_filters(event: Event, filters: Filters):
    if validate_ids(filters.ids, event.id) and validate_authors(filters.authors, event.pubkey):
        return True
    return False


class Subscription:
    def __init__(self, filters: Filters, websocket: WebSocket, subscription_id: str):
        self.filters = filters
        self.websocket = websocket
        self.subscription_id = subscription_id

    async def send(self, event: Event):
        if validate_filters(event, self.filters):
            await self.websocket.send_text(dump_json(["EVENT", self.subscription_id, event.dict()]))


class SubscriptionPool:
    def __init__(self) -> None:
        self._subscriptions: MutableSet[Subscription] = set()

    def get_subscription(self, websocket: WebSocket) -> Optional[Subscription]:
        for subscription in self._subscriptions:
            if subscription.websocket == websocket:
                return subscription

        return None

    def add_subscription(self, subscription: Subscription):
        self._subscriptions.add(subscription)

    def remove_subscription(self, subscription: Subscription):
        logger.info(f"Removing subscription: {subscription.subscription_id}")
        self._subscriptions.discard(subscription)

    async def broadcast(self, event: Event):
        _stale = []
        for subscription in self._subscriptions:
            try:
                await subscription.send(event)
            except RuntimeError:
                _stale.append(subscription)

        [self.remove_subscription(subscription) for subscription in _stale]
