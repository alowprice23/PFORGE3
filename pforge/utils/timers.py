from __future__ import annotations
import time
from contextlib import contextmanager

@contextmanager
def timer(name: str):
    start = time.time()
    yield
    end = time.time()
    print(f"[{name}] took {end - start:.2f}s")
