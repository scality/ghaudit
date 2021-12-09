
import logging
import os
from ghaudit.cli import cli


def main():
    LOGFILE = os.environ.get("LOGFILE")
    LOGLEVEL = os.environ.get("LOGLEVEL", "ERROR")
    LOG_FORMAT = '{asctime} {levelname:8s} ghaudit <{filename}:{lineno} {module}.{funcName}> {message}'
    STYLE = '{'
    if LOGFILE:
        handler = logging.FileHandler(LOGFILE)
        formatter = logging.Formatter(LOG_FORMAT, style=STYLE)
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.setLevel(LOGLEVEL)
        root.addHandler(handler)
    else:
        logging.basicConfig(
            level=LOGLEVEL, format=LOG_FORMAT, style=STYLE
        )
    # pylint: disable=no-value-for-parameter
    cli()


if __name__ == "__main__":
    main()
