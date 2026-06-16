import asyncio
from dataclasses import dataclass, field
from typing import Optional

@dataclass(order=True)
class PriorityRequest:
    priority: int
    item: object = field(compare=False)

class RequestQueue:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.processing = False
        self.queue_depth = 0

    async def execute(self, func, *args, **kwargs):
        """
        Executes a function ensuring exclusive access via a lock.
        This implements a strict FIFO queue implicitly via asyncio.Lock.
        Handles both sync and async functions.
        """
        self.queue_depth += 1
        try:
            async with self.lock:
                self.processing = True
                self.queue_depth -= 1 # We are now processing, so out of waiting queue
                try:
                    # Check if function is async
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        # Run sync function in executor
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                finally:
                    self.processing = False
        except Exception as e:
            # If we fail before acquiring lock (unlikely with this pattern)
            # or if func fails
            if self.queue_depth > 0: # Correction if something weird happened
                 pass
            raise e
            
    def get_status(self):
        return {
            "queue_depth": self.queue_depth,
            "processing": self.processing
        }
