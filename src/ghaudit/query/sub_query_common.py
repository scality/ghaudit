from typing import Any, Iterable, Mapping, MutableMapping
from ghaudit.query.utils import jinja_env
from ghaudit.query.sub_query import SubQuery, ValidValueType


class SubQueryCommon(SubQuery):
    def __init__(
        self,
        fragments: Iterable[str],
        entry: str,
        params: MutableMapping[str, str],
    ) -> None:
        SubQuery.__init__(self)
        self._entry = entry
        self._params = params
        self._values = {}  # type: MutableMapping[str, ValidValueType]

        env = jinja_env()
        self._templates = [env.get_template(frag) for frag in fragments]

    def entry(self) -> str:
        return self._entry

    def params(self) -> Mapping[str, str]:
        return self._params

    def render(self, args: Mapping[str, ValidValueType]) -> str:
        frags = [frag.render(args) for frag in self._templates]
        return "".join(frags)

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        raise NotImplementedError("abstract function call")

    def params_values(self) -> Mapping[str, ValidValueType]:
        return self._values

    def __repr__(self) -> str:
        return "{}({}): {}".format(
            self._entry, self._count, repr(self._page_info)
        )
