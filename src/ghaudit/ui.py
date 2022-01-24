"""Display formatting primitives."""

from __future__ import annotations

import json
from functools import reduce
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

DisplayMode = Literal["basic", "json", "table"]
# for some reason the "|" syntax was not accepted by mypy here. Tested with
# mypy 0.931:
ProgressItem = Union[
    Tuple[str, str],
    Tuple[str, int],
    Tuple[str, int, int],
    Tuple[str, int, int, int],
]

# the progress interface implemented by Progress
ProgressCB = Callable[[Sequence[ProgressItem]], None]


class Formatter(NamedTuple):
    table_fields: Iterable[Tuple[str, int]]
    to_fields: Callable[[Any], Iterable[Tuple[Optional[str], int]]]
    to_string: Callable[[Any], str]


def _print_list_basic(elems: Sequence[Any], fmt: Formatter) -> str:
    def format_entry(elem: Any) -> str:
        return " ◆ {}".format(fmt.to_string(elem))

    return reduce(lambda x, y: x + format_entry(y) + "\n", elems, "")


def _print_list_table(elems: Sequence[Any], fmt: Formatter) -> str:
    def mkline(cross_left: str, cross_middle: str, cross_right: str) -> str:
        return (
            cross_left
            + cross_middle.join(
                map(lambda x: "".center(x[1], "─"), fmt.table_fields)
            )
            + cross_right
            + "\n"
        )

    def format_entry(values: Iterable[Tuple[Optional[str], int]]) -> str:
        return reduce(
            lambda x, y: x + str(y[0]).center(y[1]) + "│", values, "│"
        )

    def format_item(acc_str: str, item: Any) -> str:
        return acc_str + sep_line + format_entry(fmt.to_fields(item)) + "\n"

    top = mkline("┌", "┬", "┐")
    sep_line = mkline("├", "┼", "┤")
    bottom = mkline("└", "┴", "┘")
    header = top + format_entry(fmt.table_fields) + "\n"
    return reduce(format_item, elems, header) + bottom


def _print_list_json(elems: Sequence[Any], fmt: Formatter) -> str:
    def elem_to_dict(elem: Any) -> Mapping[str, str]:
        zipped = zip(fmt.to_fields(elem), fmt.table_fields)
        return {x[1][0]: str(x[0][0]) for x in zipped}

    list_of_dicts = reduce(
        lambda x, y: x + [elem_to_dict(y)], elems, []
    )  # type: List[Mapping[str, str]]
    return json.dumps(list_of_dicts)


def _format_mode(mode: str) -> Callable[[Any, Formatter], str]:
    return {
        "basic": _print_list_basic,
        "json": _print_list_json,
        "table": _print_list_table,
    }[mode]


def _format_items(
    mode: DisplayMode, items: Iterable[Any], formatter: Formatter
) -> str:
    return _format_mode(mode)(items, formatter)


def print_items(
    mode: DisplayMode, items: Iterable[Any], formatter: Formatter
) -> None:
    """Display a list of items.

    Display a list of items according to a mode and an object to string
    formatter specification. Supported modes are json format, UTF-8 table, and
    bullet list (`basic').
    """
    print(_format_items(mode, items, formatter))


def _progress_fmt_counter(name: str, value: int | str) -> str:
    return "{}: {}".format(name, value)


def _progress_fmt_pair(name: str, finished: int, total: int) -> str:
    return "{}: {} / {}".format(name, finished, total)


def _progress_fmt_queue(
    name: str, finished: int, started: int, total: int
) -> str:
    return "{}: {} finished / {} started / {} total\n".format(
        name, finished, started, total
    )


def _progress_fmt_item(item: ProgressItem) -> str:
    dispatch_fmt = {
        2: _progress_fmt_counter,
        3: _progress_fmt_pair,
        4: _progress_fmt_queue,
    }  # type: Mapping[int, Callable[..., str]]
    return dispatch_fmt[len(item)](*item)


class Progress:
    """Generic Interface to display complexe progress metrics"""

    def __init__(self) -> None:
        self._started = False

    def __call__(self, items: Sequence[ProgressItem]) -> None:
        if not self._started:
            tcaps_up = ""
            self._started = True
        else:
            tcaps_up = "\x1B[{}A\x1b[K".format(len(items))
        print(tcaps_up + "\n".join(map(_progress_fmt_item, items)))
