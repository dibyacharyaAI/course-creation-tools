import logging
import sys

def setup_logging(service_name: str, level: str = "INFO"):
    """
    Configure structured logging for the service.
    """
    logging.basicConfig(
        level=level,
        format=f"%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(service_name)
