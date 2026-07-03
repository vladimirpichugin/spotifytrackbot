# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
from settings import Settings

from utils.logging import logger
from utils.storage import Storage


try:
    logger.info("Initializing storage..")
    storage = Storage(
        Settings.MONGO,
        Settings.MONGO_DATABASE,
        Settings.COLLECTIONS,
        server_selection_timeout_ms=Settings.MONGO_SERVER_SELECTION_TIMEOUT_MS,
    )
    logger.debug(f"MongoDB Server version: {storage.mongo_client.server_info()['version']}")
except Exception as e:
    logger.error("Failed to establish a stable connection to MongoDB", exc_info=True)
    raise RuntimeError from e
