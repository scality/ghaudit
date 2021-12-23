from tempfile import template
from typing import Any, Iterable, Mapping, MutableMapping

import jinja2

from ghaudit.query.sub_query import SubQuery, ValidValueType
import os
import sys

class SubQueryCommon(SubQuery):
    def __init__(
        self,
        fragments: Iterable[str],
        entry: str,
        params: MutableMapping[str, str],
    ) -> None:
        SubQuery.__init__(self)
        self._fragments = fragments
        self._entry = entry
        self._params = params
        self._values = {}  # type: MutableMapping[str, ValidValueType]

    def entry(self) -> str:
        return self._entry

    def params(self) -> Mapping[str, str]:
        return self._params

    def render(self, args: Mapping[str, ValidValueType]) -> str:
        
        template_dir = os.path.join(sys.prefix, 'share', 'ghaudit','fragments')

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            undefined=jinja2.StrictUndefined
        )

        frags = []
        # print(self._fragments)
        for frag in self._fragments:
            frags.append(env.get_template(frag).render(args))
        return "".join(frags)


    def update_page_info(self, response: Mapping[str, Any]) -> None:
        raise NotImplementedError("abstract function call")

    def params_values(self) -> Mapping[str, ValidValueType]:
        return self._values

    def __repr__(self) -> str:
        return "{}({}): {}".format(
            self._entry, self._count, repr(self._page_info)
        )
