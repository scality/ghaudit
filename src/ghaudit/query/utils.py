from typing import Optional, TypedDict


class PageInfo(TypedDict):
    hasNextPage: bool
    endCursor: Optional[str]


def page_info_continue(page_infos: Optional[PageInfo]) -> bool:
    if not page_infos or page_infos["hasNextPage"]:
        return True
    return False
