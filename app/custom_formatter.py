import logging
import logging.handlers
import re
import sys


class ColorCodes:
    grey = "\x1b[1;38m"
    green = "\x1b[1;32m"
    yellow = "\x1b[1;33m"
    red = "\x1b[1;31m"
    bold_red = "\x1b[31;1m"
    blue = "\x1b[1;34m"
    light_blue = "\x1b[1;36m"
    purple = "\x1b[1;35m"
    reset = "\x1b[0m"


class ColorizedArgsFormatter(logging.Formatter):
    arg_colors = [ColorCodes.purple, ColorCodes.light_blue]
    level_fields = ["levelname", "levelno"]
    level_to_color = {
        logging.DEBUG: ColorCodes.blue,
        logging.INFO: ColorCodes.green,
        logging.WARNING: ColorCodes.yellow,
        logging.ERROR: ColorCodes.red,
        logging.CRITICAL: ColorCodes.bold_red,
    }

    def __init__(self, fmt: str):
        super().__init__()
        self.level_to_formatter = {
            level: self._create_formatter(fmt, level) for level in self.level_to_color
        }

    def _create_formatter(self, fmt: str, level: int):
        color = self.level_to_color[level]
        for fld in self.level_fields:
            search = f"(%\({fld}\).*?s)"
            fmt = re.sub(search, f"{color}\\1{ColorCodes.reset}", fmt)
        return logging.Formatter(fmt)

    @staticmethod
    def is_brace_format_style(record: logging.LogRecord):
        if not record.args:
            return False

        msg = record.msg
        if "%" in msg:
            return False

        return msg.count("{") == msg.count("}") == len(record.args)

    @staticmethod
    def rewrite_record(record: logging.LogRecord):
        if not ColorizedArgsFormatter.is_brace_format_style(record):
            return

        msg = record.msg.replace("{", "{{").replace("}", "}}")
        for index, color in enumerate(ColorizedArgsFormatter.arg_colors, start=1):
            msg = msg.replace("{{", f"{color}{{", index).replace(
                "}}", f"}}{ColorCodes.reset}", index
            )

        record.msg = msg.format(*record.args)
        record.args = []

    def format(self, record):
        orig_msg, orig_args = record.msg, record.args
        formatter = self.level_to_formatter.get(record.levelno)
        self.rewrite_record(record)
        formatted = formatter.format(record)
        record.msg, record.args = orig_msg, orig_args
        return formatted


def init_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    console_level = "DEBUG"
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(console_level)
    console_format = "%(asctime)s: %(levelname)-8s: %(message)s ::: %(name)s.%(lineno)s"
    colored_formatter = ColorizedArgsFormatter(console_format)
    console_handler.setFormatter(colored_formatter)
    root_logger.addHandler(console_handler)


if __name__ == "__main__":
    init_logging()
    logger = logging.getLogger(__name__)
    logger.debug("Debug message: {0}", 123)
    logger.info("Info message: {0}", 456)
    logger.warning("Warning message: {0}", 789)
    logger.error("Error message: {0}", 101112)
    logger.critical("Critical message: {0}", 131415)
