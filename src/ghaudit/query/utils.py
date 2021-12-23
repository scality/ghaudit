from pathlib import Path
from typing import Optional, TypedDict
import sys
import jinja2


class PageInfo(TypedDict):
    hasNextPage: bool
    endCursor: Optional[str]


def page_info_continue(page_infos: Optional[PageInfo]) -> bool:
    if not page_infos or page_infos["hasNextPage"]:
        return True
    return False


def get_template_dir():
    return Path(sys.prefix) / "share" / "ghaudit" / "fragments"


def jinja_env():
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(get_template_dir()),
        undefined=jinja2.StrictUndefined,
    )
