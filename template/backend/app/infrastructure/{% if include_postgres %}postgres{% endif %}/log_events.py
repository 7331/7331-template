from app.shared.logging import LogEvent


class DatabaseClosed(LogEvent):
    message = "Database connections closed"
    operation = "database_close"
