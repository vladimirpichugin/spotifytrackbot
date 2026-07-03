from settings import Settings
from utils.json import Json
from utils.logging import logger


logger.info("Initializing localization..")
L10n = Json(Settings.L10N_RU_FILE)
