import logging
import sys


def setup_logging(
    level=logging.INFO,
    format_str="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
):
    """Setup basic logging configuration."""
    logging.basicConfig(
        level=level, format=format_str, handlers=[logging.StreamHandler(sys.stdout)]
    )
    # Suppress noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
