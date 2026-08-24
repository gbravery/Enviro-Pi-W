import uasyncio as asyncio

_subscribers = {}

def clear():
    """Clears all registered subscribers. Ensures clean state across restarts."""
    global _subscribers
    _subscribers = {}

def subscribe(event_name, callback):
    """Registers a component to listen for a specific event type."""
    if event_name not in _subscribers:
        _subscribers[event_name] = []
    if callback not in _subscribers[event_name]:
        _subscribers[event_name].append(callback)

async def _dispatch_task(callback, *args, **kwargs):
    """Internal worker that catches both synchronous and asynchronous operations safely."""
    try:
        result = callback(*args, **kwargs)
        # If the result is a coroutine or generator, await it cleanly
        if hasattr(result, '__await__') or hasattr(result, 'send') or hasattr(result, '__iter__'):
            await result
    except Exception as e:
        print(f"[EventBus] Execution crash during callback: {e}")

def publish(event_name, *args, **kwargs):
    """
    Fires an event cleanly. Wraps callbacks into asynchronous execution workers 
    to prevent race conditions on the single-threaded MicroPython loop.
    """
    if event_name in _subscribers:
        for callback in _subscribers[event_name]:
            # Schedule every callback through an isolated background micro-task wrapper
            asyncio.create_task(_dispatch_task(callback, *args, **kwargs))

