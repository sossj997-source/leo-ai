import time
import logging

logger = logging.getLogger("JARVIS")

def with_retry(func, max_retries: int = 2, initial_delay: float = 0.5):
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                logger.warning(f"Retrying {func.__name__} due to: {e}")
                time.sleep(delay)
                delay *= 2 
            else:
                raise last_exception