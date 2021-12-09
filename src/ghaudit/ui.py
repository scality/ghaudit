from functools import reduce
from collections import namedtuple
import json


Formatter = namedtuple('Formatter', 'table_fields to_fields to_string')


def _print_list_basic(elems, fmt):
    def format_entry(elem):
        return ' * {}'.format(fmt.to_string(elem))

    return reduce(lambda x, y: x + format_entry(y) + '\n', elems, '')


def _print_list_table(elems, fmt):
    def mkline(cross_left, cross_middle, cross_right):
        return cross_left \
            + cross_middle.join(map(lambda x: ''.center(x[1], '─'),
                                    fmt.table_fields)) \
            + cross_right + '\n'

    def format_entry(values):
        return reduce(lambda x, y: x + str(y[0]).center(y[1]) + '│',
                      values, '│')

    def format_item(acc_str, item):
        return acc_str + sep_line + format_entry(fmt.to_fields(item)) + '\n'

    top = mkline('┌', '┬', '┐')
    sep_line = mkline('├', '┼', '┤')
    bottom = mkline('└', '┴', '┘')
    header = top \
        + format_entry(fmt.table_fields) \
        + '\n'
    return reduce(format_item, elems, header) + bottom


def _print_list_json(elems, fmt):
    def elem_to_dict(elem):
        zipped = zip(fmt.to_fields(elem), fmt.table_fields)
        return {x[1][0]: x[0][0] for x in zipped}

    list_of_dicts = reduce(lambda x, y: x + [elem_to_dict(y)], elems, [])
    return json.dumps(list_of_dicts)


def format_mode(mode):
    return {
        'basic': _print_list_basic,
        'json': _print_list_json,
        'table': _print_list_table,
    }[mode]


def format_items(mode, items, formatter):
    return format_mode(mode)(items, formatter)


def print_items(mode, items, formatter):
    print(format_items(mode, items, formatter))
