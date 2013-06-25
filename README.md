python-debug-utils
==================

log_open.py: module that monkey patches __builtin__.open and
             socket.connect, and generates a report showing where
             they were called from. Just import to use, it sets
             up an atexit() handler

debug_logger.py: sets up a log handler for stdout, and has a colorized
                 log formatted. Sometimes useful for tracking down
                 threading issues, etc
