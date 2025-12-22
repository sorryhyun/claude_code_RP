"""
File locking utilities for safe concurrent file writes.

This module provides thread-safe and process-safe file locking mechanisms
to prevent race conditions when multiple agents write to the same config files.

Platform Support:
- POSIX systems (Linux, macOS): Uses fcntl for process-safe file locking
- Windows: Uses msvcrt for file locking, or threading.Lock as fallback
"""

import logging
import os
import sys
import threading
from contextlib import contextmanager

# Platform-specific imports
try:
    import fcntl

    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
    # Windows fallback
    if sys.platform == "win32":
        try:
            import msvcrt

            HAS_MSVCRT = True
        except ImportError:
            HAS_MSVCRT = False
    else:
        HAS_MSVCRT = False

logger = logging.getLogger("FileLocking")

# Fallback lock for systems without fcntl or msvcrt
_file_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_thread_lock(file_path: str) -> threading.Lock:
    """Get or create a threading.Lock for the given file path."""
    with _locks_lock:
        if file_path not in _file_locks:
            _file_locks[file_path] = threading.Lock()
        return _file_locks[file_path]


@contextmanager
def file_lock(file_path: str, mode: str = "a"):
    """
    Context manager for cross-platform file locking.

    This prevents race conditions when multiple agents try to write to the
    same file concurrently (e.g., memory.md, recent_events.md).

    Platform-specific implementation:
    - POSIX (Linux, macOS): Uses fcntl for process-safe locking
    - Windows: Uses msvcrt for file locking
    - Fallback: Uses threading.Lock (thread-safe only, not process-safe)

    Usage:
        with file_lock('/path/to/file.txt', 'a') as f:
            f.write('new content\\n')

    Args:
        file_path: Path to the file to lock
        mode: File open mode ('a' for append, 'w' for write, 'r+' for read+write)

    Yields:
        File handle with exclusive lock

    Raises:
        IOError: If file cannot be opened or locked
    """
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Get threading lock as fallback
    thread_lock = None
    if not HAS_FCNTL and not HAS_MSVCRT:
        thread_lock = _get_thread_lock(file_path)
        thread_lock.acquire()
        logger.debug(f"Acquired thread lock on {file_path} (fallback mode)")

    # Open file in specified mode
    f = None
    try:
        f = open(file_path, mode, encoding="utf-8")

        # Acquire platform-specific file lock
        if HAS_FCNTL:
            # POSIX: Use fcntl for process-safe locking
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            logger.debug(f"Acquired fcntl lock on {file_path}")
        elif HAS_MSVCRT:
            # Windows: Use msvcrt for file locking
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            logger.debug(f"Acquired msvcrt lock on {file_path}")
        # else: Already acquired thread lock above

        yield f

    finally:
        if f:
            # Release platform-specific lock
            try:
                if HAS_FCNTL:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    logger.debug(f"Released fcntl lock on {file_path}")
                elif HAS_MSVCRT:
                    try:
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                        logger.debug(f"Released msvcrt lock on {file_path}")
                    except Exception:
                        # File may already be unlocked on close
                        pass
            except Exception as e:
                logger.warning(f"Error releasing file lock on {file_path}: {e}")
            finally:
                f.close()

        # Release thread lock if used
        if thread_lock:
            thread_lock.release()
            logger.debug(f"Released thread lock on {file_path}")


def safe_append_line(file_path: str, line: str) -> bool:
    """
    Safely append a line to a file with file locking.

    Args:
        file_path: Path to the file
        line: Line to append (newline will be added automatically)

    Returns:
        True if successful, False otherwise
    """
    try:
        with file_lock(file_path, "a") as f:
            # Ensure line ends with newline
            if not line.endswith("\n"):
                line += "\n"
            f.write(line)
        return True
    except Exception as e:
        logger.error(f"Error appending to {file_path}: {e}")
        return False


def safe_read_file(file_path: str) -> str:
    """
    Safely read a file with shared lock.

    Args:
        file_path: Path to the file

    Returns:
        File contents as string, or empty string if file doesn't exist
    """
    if not os.path.exists(file_path):
        return ""

    # Get threading lock as fallback
    thread_lock = None
    if not HAS_FCNTL and not HAS_MSVCRT:
        thread_lock = _get_thread_lock(file_path)
        thread_lock.acquire()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Acquire platform-specific shared lock for reading
            if HAS_FCNTL:
                # POSIX: Use shared lock for concurrent reads
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            elif HAS_MSVCRT:
                # Windows: msvcrt doesn't support shared locks, use exclusive
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            # else: Already acquired thread lock above

            try:
                content = f.read()
            finally:
                # Release platform-specific lock
                if HAS_FCNTL:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                elif HAS_MSVCRT:
                    try:
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass  # May already be unlocked on close
        return content
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return ""
    finally:
        # Release thread lock if used
        if thread_lock:
            thread_lock.release()
