import asyncio
from typing import Dict, Any, Callable, Awaitable, Optional, List

_OBSERVATIONS: Dict[str, Dict] = {}
_OBSERVERS: List[Callable[[str, str, Any], Awaitable[None]]] = []


def record_observation(trace_id: str, plan: Dict, counts: Dict[str, int]) -> None:
    _OBSERVATIONS[trace_id] = {
        "plan": plan,
        "counts": counts,
    }


def register_observer(observer: Callable[[str, str, Any], Awaitable[None]]) -> None:
    """Register an observer function to receive node updates.
    
    The observer function should accept:
    - node_id: str - The ID of the node
    - status: str - The status of the node ('pending', 'in_progress', 'completed', 'error')
    - content: Any - The content of the node update
    """
    if observer not in _OBSERVERS:
        _OBSERVERS.append(observer)


def notify_observers(node_id: str, status: str, content: Any = None) -> None:
    """Notify all observers of a node update."""
    if not _OBSERVERS:
        return
    
    # Store the updates to be processed by the main thread
    from functools import partial
    
    for observer in _OBSERVERS:
        try:
            # Create a partial function that can be called later
            callback = partial(observer, node_id, status, content)
            
            # Add a special attribute to identify this as a pending observer callback
            setattr(callback, "_observer_callback", True)
            setattr(callback, "_node_id", node_id)
            setattr(callback, "_status", status)
            
            # Store the callback in a global list that will be checked by the main thread
            _PENDING_CALLBACKS.append(callback)
            
            # Print debug info
            print(f"[DEBUG] Queued update for {node_id}: {status}")
        except Exception as e:
            print(f"Error preparing observer notification: {e}")

# Global list to store pending callbacks
_PENDING_CALLBACKS = []

# Function to process pending callbacks from the main thread
async def process_pending_callbacks():
    """Process any pending callbacks that were queued from other threads."""
    global _PENDING_CALLBACKS
    
    if not _PENDING_CALLBACKS:
        return
    
    # Get all pending callbacks
    callbacks = _PENDING_CALLBACKS.copy()
    _PENDING_CALLBACKS.clear()
    
    # Process each callback
    for callback in callbacks:
        try:
            node_id = getattr(callback, "_node_id", "unknown")
            status = getattr(callback, "_status", "unknown")
            print(f"[DEBUG] Processing queued update for {node_id}: {status}")
            await callback()
        except Exception as e:
            print(f"Error processing observer callback: {e}")

