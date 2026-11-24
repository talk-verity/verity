from collections import deque
from threading import Lock
from time import monotonic
from fastapi import HTTPException

_lock = Lock()
_windows = {}

def check_rate(user_id: str):
    now = monotonic()
    with _lock:
        stale = [key for key, values in _windows.items() if not values or values[-1] <= now - 60]
        for key in stale:
            del _windows[key]
        if user_id not in _windows and len(_windows) >= 10000:
            raise HTTPException(429, "Service busy. Try again shortly.")
        window = _windows.setdefault(user_id, deque())
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= 60:
            raise HTTPException(429, "Request limit reached. Try again shortly.", headers={"Retry-After": "60"})
        window.append(now)
