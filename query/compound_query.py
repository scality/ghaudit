import functools
import json

import jinja2
import requests

from ghaudit.query.utils import page_info_continue

GITHUB_GRAPHQL_ENDPOINT = 'https://api.github.com/graphql'


# TODO move this somewhere else
def github_graphql_call(call_str, auth_driver, variables):
    # print({'query': call_str, 'variables': json.dumps(variables)})
    result = requests.post(
        GITHUB_GRAPHQL_ENDPOINT,
        json={'query': call_str, 'variables': json.dumps(variables)},
        headers=auth_driver()
    )
    if result.status_code != 200:
        error_fmt = (
            'Call failed to run by returning code of {}.'
            'Error message: {}.'
            'Query: {}'
        )
        raise Exception(error_fmt.format(
            result.status_code,
            result.text,
            call_str[:200]
        ))
    return result.json()


class CompoundQuery2():
    FRAG_ENTRY_MAIN = """
query org_infos({% for name, type in params.items() %}${{ name }}: {{ type }}{% if not loop.last %}, {% endif %}{% endfor %}) {
    {%- for fragment in fragments %}
    ...{{ fragment }}
    {%- endfor %}
}
"""

    def __init__(self, max_parallel):
        self._sub_queries = []
        self._common_frags = []
        self._max_parallel = max_parallel
        self._queue = []

    # check for contention so that max_parallel
    # is respected
    def _parallel_wait(self):
        return len(self._sub_queries) >= self._max_parallel

    def _append(self, sub_query):
        self._sub_queries.append(sub_query)

    def append(self, sub_query):
        if self._parallel_wait():
            self._queue.append(sub_query)
        else:
            self._sub_queries.append(sub_query)

    def render(self):
        params = functools.reduce(lambda x, y: {**x, **y.params()}, self._sub_queries, {})
        common_fragments = ''.join(self._common_frags)
        fragments = [x.entry() for x in self._sub_queries]
        main_frag = jinja2.Template(
            CompoundQuery2.FRAG_ENTRY_MAIN).render(
                {
                    'params': params,
                    'fragments': fragments
                }
            )
        # render query entry point
        sub_renders = ''.join([x.render({'page_infos': x.get_page_info()}) for x in self._sub_queries])
        return common_fragments + sub_renders + main_frag

    def _dequeue(self):
        while self._queue and not self._parallel_wait():
            self._append(self._queue.pop())

    def run(self, auth_driver, args):
        assert self._queue or self._sub_queries

        # TODO verify all parameters:
        #  * no unknown param
        #  * no param with without a value
        rendered = self.render()
        # print(rendered)
        # print('===============')

        self._dequeue()
        for sub_query in self._sub_queries:
            print(repr(sub_query))
            args = {**sub_query.params_values(), **args}
        # print(args)
        result = github_graphql_call(rendered, auth_driver, args)
        # print(result)
        # print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>')

        # TODO maybe check for errors here

        to_remove = []
        if 'data' not in result:
            print(result)
            assert False
        for sub_query in self._sub_queries:
            sub_query.update_page_info(result['data'])
            if not page_info_continue(sub_query.get_page_info()):
                to_remove.append(sub_query)
        for value in to_remove:
            self._sub_queries.remove(value)
        return result

    def finished(self):
        return not self._sub_queries and not self._queue

    def add_frag(self, frag):
        self._common_frags.append(frag)

    def size(self):
        return len(self._sub_queries)
