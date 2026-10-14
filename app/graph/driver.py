import logging
import threading
from typing import Optional, Tuple
from neo4j import GraphDatabase, Driver, exceptions as neo4j_exceptions
from backend.core.config import Settings, get_settings

logger = logging.getLogger("mediscanai.graph.driver")

_driver_lock = threading.Lock()
_global_driver: Optional[Driver] = None


def create_neo4j_driver(
    uri: str,
    auth: Tuple[str, str],
    connection_timeout: float = 5.0,
    max_connection_lifetime: float = 3600.0,
    max_connection_pool_size: int = 50,
) -> Driver:
    """
    Explicit factory function to create a configured Neo4j Driver instance.
    Does not establish immediate network connections upon instantiation;
    connections are created lazily or verified explicitly.
    """
    logger.debug("Creating Neo4j driver for URI: %s", uri)
    return GraphDatabase.driver(
        uri,
        auth=auth,
        connection_timeout=connection_timeout,
        max_connection_lifetime=max_connection_lifetime,
        max_connection_pool_size=max_connection_pool_size,
    )


def get_neo4j_driver(settings: Optional[Settings] = None) -> Optional[Driver]:
    """
    Returns the application-wide Neo4j driver instance.
    If NEO4J_ENABLED is False, returns None without attempting any connection.
    Thread-safe lazy initialization.
    """
    global _global_driver

    if _global_driver is not None:
        return _global_driver

    cfg = settings or get_settings()
    if not cfg.NEO4J_ENABLED:
        logger.debug("Neo4j is disabled (NEO4J_ENABLED=False). Bypassing driver creation.")
        return None

    with _driver_lock:
        if _global_driver is None:
            logger.info("Initializing Neo4j driver connection to %s", cfg.NEO4J_URI)
            _global_driver = create_neo4j_driver(
                uri=cfg.NEO4J_URI,
                auth=(cfg.NEO4J_USER, cfg.NEO4J_PASSWORD),
                connection_timeout=cfg.NEO4J_CONNECTION_TIMEOUT_SECONDS,
                max_connection_lifetime=cfg.NEO4J_MAX_CONNECTION_LIFETIME_SECONDS,
                max_connection_pool_size=cfg.NEO4J_MAX_CONNECTION_POOL_SIZE,
            )
        return _global_driver


def verify_neo4j_connectivity(driver: Optional[Driver] = None) -> bool:
    """
    Verifies that the Neo4j instance is reachable and credentials are valid.
    Returns True if connectivity is established, False otherwise.
    Operational connection errors are logged clearly without swallowing unexpected exceptions.
    """
    target_driver = driver or get_neo4j_driver()
    if target_driver is None:
        logger.warning("Neo4j connectivity check skipped: driver is not configured or disabled.")
        return False

    try:
        target_driver.verify_connectivity()
        logger.info("Neo4j connectivity verified successfully.")
        return True
    except (neo4j_exceptions.DriverError, neo4j_exceptions.Neo4jError) as exc:
        logger.warning("Neo4j connectivity verification failed: %s (%s)", type(exc).__name__, exc)
        return False


def close_neo4j_driver(driver: Optional[Driver] = None) -> None:
    """
    Cleanly closes the given driver or the global cached driver instance.
    Thread-safe cleanup.
    """
    global _global_driver

    with _driver_lock:
        if driver is not None:
            try:
                driver.close()
                logger.debug("Explicit Neo4j driver closed successfully.")
            except Exception as exc:
                logger.error("Error closing explicit Neo4j driver: %s", exc, exc_info=True)
            if driver is _global_driver:
                _global_driver = None
        elif _global_driver is not None:
            try:
                _global_driver.close()
                logger.info("Global Neo4j driver closed successfully.")
            except Exception as exc:
                logger.error("Error closing global Neo4j driver: %s", exc, exc_info=True)
            finally:
                _global_driver = None
