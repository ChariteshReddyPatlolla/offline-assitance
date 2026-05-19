import contextvars

# Thread-safe and async-safe request context variable to store the active session's current working directory
active_session_dir = contextvars.ContextVar("active_session_dir", default=None)
