import sys
import os
from loguru import logger

def setup_app_logging():
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logger.remove()

    logger.add(
        sys.stdout, 
        colorize=True, 
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    logger.add(
        "logs/tourist_app.log", 
        rotation="1 week",     
        retention="1 month",   
        level="INFO",          
        compression="zip",
        enqueue=True,
        delay=True 
    )
    
    return logger