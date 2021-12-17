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
)

DisplayMode = Literal["basic", "json", "table"]


class Formatter(NamedTuple):
    table_fields: Iterable[Tuple[str, int]]
    to_fields: Callable[[Any], Iterable[Tuple[Optional[str], int]]]
    to_string: Callable[[Any], str]


def _print_list_basic(elems: Sequence[Any], fmt: Formatter) -> str:
    def format_entry(elem: Any) -> str:
        return " * {}".format(fmt.to_string(elem))

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


def format_mode(mode: str) -> Callable[[Any, Formatter], str]:
    return {
        "basic": _print_list_basic,
        "json": _print_list_json,
        "table": _print_list_table,
    }[mode]


def format_items(
    mode: DisplayMode, items: Iterable[Any], formatter: Formatter
) -> str:
    return format_mode(mode)(items, formatter)


def print_items(
    mode: DisplayMode, items: Iterable[Any], formatter: Formatter
) -> None:
    print(format_items(mode, items, formatter))
