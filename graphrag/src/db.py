from __future__ import annotations
import logging
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable
import config
logger = logging.getLogger(__name__)

def get_driver() -> Driver:
    try:
        driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD),
        )
        driver.verify_connectivity()
        logger.info("Conexión con Neo4j Desktop verificada correctamente.")
        return driver
    except AuthError:
        logger.error("Credenciales incorrectas.")
        raise
    except ServiceUnavailable:
        logger.error(
            "No se pudo conectar a Neo4j Desktop."
        )
        raise
    except Neo4jError:
        logger.exception("Error de Neo4j al inicializar el driver.")
        raise
