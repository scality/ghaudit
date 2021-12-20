from typing import Any, Mapping, Optional, Union

from ghaudit.query.utils import PageInfo

ValidValueType = Union[str, int, PageInfo, None]


class SubQuery:
    def __init__(self) -> None:
        self._page_info = None  # type: Optional[PageInfo]
        self._count = 0

    def render(self, args: Mapping[str, ValidValueType]) -> str:
        raise NotImplementedError("abstract function call")

    def entry(self) -> str:
        raise NotImplementedError("abstract function call")

    def params(self) -> Mapping[str, str]:
        raise NotImplementedError("abstract function call")

    def get_page_info(self) -> Optional[PageInfo]:
        return self._page_info

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        raise NotImplementedError("abstract function call")

    def params_values(self) -> Mapping[str, ValidValueType]:
        raise NotImplementedError("abstract function call")
