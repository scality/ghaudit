import sys
from pathlib import Path
from typing import Optional, TypedDict

import jinja2


class PageInfo(TypedDict):
    hasNextPage: bool
    endCursor: Optional[str]


def page_info_continue(page_infos: Optional[PageInfo]) -> bool:
    return not page_infos or page_infos["hasNextPage"]


def get_template_dir() -> Path:
    return Path(sys.prefix) / "share" / "ghaudit" / "fragments"


def jinja_env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(get_template_dir()),
        undefined=jinja2.StrictUndefined,
        autoescape=True,
    )
