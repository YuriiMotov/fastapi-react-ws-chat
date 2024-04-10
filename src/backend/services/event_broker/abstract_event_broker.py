import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import AsyncIterator

from pydantic import TypeAdapter

from backend.schemas.event import AnyEvent, AnyEventDiscr
from backend.services.event_broker.event_broker_exc import (
    EventBrokerException,
    EventBrokerFail,
)

USE_CONTEXT_ERROR = (
    "EventBroker should be used as a async context manager. "
    "Example: `async with event_broker.session(user_uuid):`"
)
ACK_TIMEOUT_SEC = 2


@dataclass
class UnacknowledgedEvents:
    expire_dt: datetime
    sent_events: list[AnyEvent]


@contextmanager
def handle_exceptions(*args, **kwds):
    """
    Intercept exceptions and raise EventBrokerFail exceptions
    """
    try:
        yield
    except EventBrokerException as exc:
        raise EventBrokerFail(detail=exc.detail)
    except Exception as exc:
        raise EventBrokerFail(detail=f"{exc}")


class AbstractEventBroker(ABC):

    def __init__(self):
        self._unacknowledged_events: dict[int, UnacknowledgedEvents | None] = (
            defaultdict(None)
        )

    @asynccontextmanager
    async def session(self, user_id: uuid.UUID) -> AsyncIterator[None]:
        """
        Context manager for managing session.
        Will create new session on Enter and close it (removes queue) on Exit.

        Raises:
         - EventBrokerFail in case of Event broker failure
        """
        async with self._session(user_id=user_id):
            self._unacknowledged_events[user_id.int] = None
            yield
            self._unacknowledged_events[user_id.int] = None

    @abstractmethod
    @asynccontextmanager
    async def _session(self, user_id: uuid.UUID) -> AsyncIterator[None]:
        """
        Abstract method to manage session that should be implemented in the derived
        class.
        Only for internal use. Don't use it in your code!
        """
        raise NotImplementedError()
        yield

    @abstractmethod
    async def subscribe(self, channel: str, user_id: uuid.UUID):
        """
        Subscribe user to all new events in specific channel.

        Raises:
         - EventBrokerFail in case of Event broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        """
        Subscribe user to all new events in all channels in the list.

        Raises:
         - EventBrokerFail in case of Event broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def _get_events_str(
        self, user_id: uuid.UUID, limit: int | None = None
    ) -> list[str]:
        """
        Return all new events for specific user as a list of strings.
        Abstract method that should be implemented in the derived class.
        Only for internal use. Don't use it in your code!

        Raises:
         - EventBrokerUserNotSubscribedError if user isn't subscribed
         - EventBrokerFail in case of Event broker failure
        """
        raise NotImplementedError()

    async def get_events(
        self, user_id: uuid.UUID, limit: int | None = None
    ) -> list[AnyEvent]:
        """
        Return all new events for specific user.

        Raises:
         - EventBrokerUserNotSubscribedError if user isn't subscribed
         - EventBrokerFail in case of Event broker failure
        """
        with handle_exceptions():
            user_id_int = user_id.int
            if unack_data := self._unacknowledged_events[user_id_int]:
                if unack_data.sent_events:
                    if unack_data.expire_dt > datetime.now():
                        return []  # Waiting for aknowledgment of previous events
                    else:
                        # Ack timeout reached. Send previous events again
                        unack_data.expire_dt = datetime.now() + timedelta(
                            seconds=ACK_TIMEOUT_SEC
                        )
                        return unack_data.sent_events
                self._unacknowledged_events[user_id_int] = None

            events = await self._get_events_str(user_id=user_id, limit=limit)
            event_adapter: TypeAdapter[AnyEvent] = TypeAdapter(
                AnyEventDiscr  # type: ignore[arg-type]
            )
            events_validated = [event_adapter.validate_json(event) for event in events]

            if events_validated:
                self._unacknowledged_events[user_id_int] = UnacknowledgedEvents(
                    expire_dt=(datetime.now() + timedelta(seconds=ACK_TIMEOUT_SEC)),
                    sent_events=events_validated,
                )
            return events_validated

    async def acknowledge_events(self, user_id: uuid.UUID) -> list[AnyEvent]:
        """
        Acknowledge receiving the list of events.
        Returns list of events that were acknowledged by this call.
        """
        with handle_exceptions():
            acknowledged_events = self._unacknowledged_events[user_id.int]
            self._unacknowledged_events[user_id.int] = None
            return acknowledged_events.sent_events if acknowledged_events else []

    @abstractmethod
    async def _post_event_str(self, channel: str, event: str):
        """
        Post new event (string representation) to the specific channel.
        Abstract method that should be implemented in the derived class.
        Only for internal use. Don't use it in your code!

        Raises:
         - EventBrokerFail in case of Event broker failure
        """
        raise NotImplementedError()

    async def post_event(self, channel: str, event: AnyEvent):
        """
        Post new event to the specific channel.

        Raises:
         - EventBrokerFail in case of Event broker failure
        """
        with handle_exceptions():
            await self._post_event_str(channel=channel, event=event.model_dump_json())
