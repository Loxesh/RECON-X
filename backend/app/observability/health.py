
from fastapi import Request


def get_database_health(request: Request) -> bool:
    """
    Return the MongoDB connectivity status stored
    in the FastAPI application state.
    """

    return bool(
        getattr(request.app.state, "mongodb_healthy", False)
    )
