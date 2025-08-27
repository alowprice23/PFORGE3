from __future__ import annotations
import os
import time

class FileLockException(Exception):
    """Raised when a lock could not be acquired."""
    pass

class FileLock:
    """
    A cross-platform file locking context manager.

    This implementation uses a common strategy of creating a `.lock` file.
    It's process-safe and works on both Unix and Windows.
    """

    def __init__(self, file_path: str, timeout: int = 10):
        """
        Prepare the file lock.

        Args:
            file_path: The path to the file to lock.
            timeout: The number of seconds to wait for the lock.
        """
        self.is_locked = False
        # Create a lock file in the same directory as the target file.
        self.lockfile = os.path.abspath(file_path + ".lock")
        self.timeout = timeout

    def acquire(self):
        """
        Acquire the lock, waiting until the timeout is reached.
        """
        start_time = time.time()
        while True:
            try:
                # The O_CREAT | O_EXCL flags make os.open atomic.
                # It will fail if the file already exists.
                self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                self.is_locked = True
                break
            except OSError as e:
                # In Python 3.3+, FileExistsError is a subclass of OSError.
                if e.errno != 17: # errno.EEXIST
                    raise
                if (time.time() - start_time) >= self.timeout:
                    raise FileLockException(f"Timeout waiting for lock on {self.lockfile}")
                time.sleep(0.1)

    def release(self):
        """
        Release the lock by closing and deleting the lock file.
        """
        if self.is_locked:
            os.close(self.fd)
            os.unlink(self.lockfile)
            self.is_locked = False

    def __enter__(self):
        """Acquire the lock when entering the 'with' statement."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Release the lock when exiting the 'with' statement."""
        self.release()

    def __del__(self):
        """
        A destructor to ensure the lock is released if the object is
        garbage collected.
        """
        self.release()
