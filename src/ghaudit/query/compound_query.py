import functools
import json
import logging
from typing import Any, List, Mapping, Set, TypedDict

import requests

from ghaudit import utils
from ghaudit.auth import AuthDriver
from ghaudit.query.sub_query import SubQuery, ValidValueType
from ghaudit.query.utils import jinja_env, page_info_continue


class Stats(TypedDict):
    iterations: int
    queries: int
    done: int


class CompoundQuery:
    def __init__(self, max_parallel: int) -> None:
        self._sub_queries = []  # type: List[SubQuery]
        self._common_frags = []  # type: List[str]
        self._max_parallel = max_parallel
        self._queue = []  # type: List[SubQuery]
        self._stats = {
            "iterations": 0,
            "queries": 0,
            "done": 0,
        }  # type: Stats
        self._session = requests.session()
        self._render_entry_point = jinja_env().get_template(
            "compound_query.j2"
        )

    def _parallel_wait(self) -> bool:
        """Check for contention so that max_parallel is respected."""
        return len(self._sub_queries) >= self._max_parallel

    def _append(self, sub_query: SubQuery) -> None:
        self._sub_queries.append(sub_query)

    def append(self, sub_query: SubQuery) -> None:
        self._stats["queries"] += 1
        if self._parallel_wait():
            self._queue.append(sub_query)
        else:
            self._sub_queries.append(sub_query)

    def _verify_params(self, args: Mapping[str, ValidValueType]) -> None:
        declared = set()  # type: Set[str]
        assigned = set(args.keys())  # type: Set[str]
        for sub_query in self._sub_queries:
            sub_query_params = frozenset(sub_query.params().keys())
            sub_query_values = frozenset(sub_query.params_values().keys())
            declared |= sub_query_params
            assigned |= sub_query_values
        unassigned = declared - assigned
        undeclared = declared - assigned
        if unassigned:
            raise RuntimeError(
                "parameters declared but not assigned: {}".format(
                    declared - assigned
                )
            )
        if undeclared:
            raise RuntimeError(
                "parameters assigned but not declared: {}".format(
                    assigned - declared
                )
            )

    def render(self) -> str:
        params = functools.reduce(
            lambda x, y: {**x, **y.params()}, self._sub_queries, {}
        )  # type: Mapping[str, str]
        common_fragments = "".join(self._common_frags)
        fragments = [x.entry() for x in self._sub_queries]

        main_frag = self._render_entry_point.render(
            {"params": params, "fragments": fragments}
        )
        sub_renders = "".join(
            [
                x.render({"page_infos": x.get_page_info()})
                for x in self._sub_queries
            ]
        )
        return common_fragments + sub_renders + main_frag

    def _dequeue(self) -> None:
        while self._queue and not self._parallel_wait():
            self._append(self._queue.pop())

    def run(
        self, auth_driver: AuthDriver, args: Mapping[str, ValidValueType]
    ) -> Mapping[str, Any]:
        if not self._queue and not self._sub_queries:
            raise RuntimeError("Nothing to do")

        self._dequeue()
        self._verify_params(args)
        rendered = self.render()

        for sub_query in self._sub_queries:
            args = {**sub_query.params_values(), **args}
        self._stats["iterations"] += 1
        result = utils.github_graphql_call(
            rendered, auth_driver, args, self._session
        )

        to_remove = []
        if "data" not in result:
            raise RuntimeError(
                'Invalid response from github: "{}"'.format(json.dumps(result))
            )

        logging.debug("response: %s", utils.LazyJsonFmt(result))

        for sub_query in self._sub_queries:
            sub_query.update_page_info(result["data"])
            if not page_info_continue(sub_query.get_page_info()):
                to_remove.append(sub_query)
        for value in to_remove:
            self._sub_queries.remove(value)
            self._stats["done"] += 1
        return result

    def finished(self) -> bool:
        return not self._sub_queries and not self._queue

    def add_frag(self, frag: str) -> None:
        self._common_frags.append(frag)

    def size(self) -> int:
        return len(self._sub_queries)

    def stats(self) -> Stats:
        return self._stats
