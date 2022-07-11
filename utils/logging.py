import logging
import sys
from loguru import logger


# Intercept logging and send to loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger():
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    # logger.add(
    #     "logs/mitbot_{time}.log",
    #     compression="zip",
    #     rotation="50 MB",
    #     retention="60 days",
    # )
