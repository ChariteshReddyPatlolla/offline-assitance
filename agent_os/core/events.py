import asyncio
from typing import Any, Callable, Dict, List
from pydantic import BaseModel

class EventMessage(BaseModel):
    """Strongly typed event message."""
    event_type: str
    source: str
    payload: Dict[str, Any]

class EventBus:
    """
    Enhanced in-memory publish-subscribe event bus for agent and system communication.
    Supports asynchronous message passing.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[EventMessage], Any]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[EventMessage], Any]):
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def publish(self, message: EventMessage):
        """Publish an event to all subscribers."""
        if message.event_type in self._subscribers:
            callbacks = self._subscribers[message.event_type]
            await asyncio.gather(*(callback(message) for callback in callbacks))
            
event_bus = EventBus()
