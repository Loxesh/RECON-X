
from pymongo import MongoClient
from pymongo.server_api import ServerApi

from app.core.config import settings


def create_mongo_client() -> MongoClient:
    """
    Create the application's synchronous MongoDB client.

    The client is created once during application startup
    and closed during application shutdown.
    """

    if settings.mongodb_uri is None:
        raise RuntimeError("MongoDB URI is not configured.")

    return MongoClient(
        settings.mongodb_uri.get_secret_value(),
        server_api=ServerApi("1"),
        serverSelectionTimeoutMS=(
            settings.mongodb_server_selection_timeout_ms
        ),
        connectTimeoutMS=settings.mongodb_connect_timeout_ms,
        socketTimeoutMS=settings.mongodb_socket_timeout_ms,
        maxPoolSize=settings.mongodb_max_pool_size,
    )


def ping_mongodb(client: MongoClient) -> bool:
    """
    Check whether MongoDB is reachable.
    """

    try:
        client.admin.command("ping")
        return True
    except Exception:
        return False


def close_mongo_client(client: MongoClient | None) -> None:
    """
    Close the MongoDB client safely.
    """

    if client is not None:
        client.close()
