from sys import stdout
from logging import getLogger, StreamHandler, Formatter, Logger
from logging.handlers import TimedRotatingFileHandler
from typing import Optional
from os import makedirs, getenv
from os.path import join as joinpath

from .models import LogLevel
from ..config import DevConfig


def setup_logger(name: str = "PC", level: Optional[LogLevel] = None) -> Logger:
    logger = getLogger(name)

    if logger.handlers:
        return logger
    
    if level is not None:
        logger.setLevel(level=level.value)
    else:
        # TODO: check environment and set based on level
        logger.setLevel(level=LogLevel.DEBUG.value)

    # Output to stream
    stream_handler = StreamHandler(stream=stdout)
    formatter = Formatter(
        '%(asctime)s %(name)s-%(levelname)s %(message)s',
        datefmt='%m/%d %H:%M:%S'
    )
    stream_handler.setFormatter(fmt=formatter)
    logger.addHandler(hdlr=stream_handler)

    if not getenv("GAE_ENV"):
        # Daily rotating file handler with directory, if not on GAE
        makedirs(DevConfig.LOG_DIR, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            joinpath(DevConfig.LOG_DIR, 'app.log'), 
            when='midnight', 
            interval=1
        )
        file_handler.setFormatter(fmt=formatter)
        logger.addHandler(hdlr=file_handler)

    return logger

