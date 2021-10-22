
import logging
import os
from ghaudit.cli import cli

if __name__ == "__main__":
    LOGFILE = os.environ.get("LOGFILE")
    LOGLEVEL = os.environ.get("LOGLEVEL", "ERROR")
    log_format = '{asctime} {levelname:8s} ghaudit <{filename}:{lineno} {module}.{funcName}> {message}'
    style='{'
    if LOGFILE:
        handler = logging.FileHandler(LOGFILE)
        formatter = logging.Formatter(log_format, style=style)
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.setLevel(LOGLEVEL)
        root.addHandler(handler)
    else:
        logging.basicConfig(
            level=LOGLEVEL, format=log_format, style=style
        )
    #pylint: disable=no-value-for-parameter
    cli()
