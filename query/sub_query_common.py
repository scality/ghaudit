
import jinja2


from ghaudit.query.sub_query import SubQuery


class SubQueryCommon(SubQuery):
    def __init__(self, fragments, entry, params):
        SubQuery.__init__(self)
        self._fragments = fragments
        self._entry = entry
        self._params = params
        self._values = {}

    def entry(self):
        return self._entry

    def params(self):
        return self._params

    def render(self, args):
        template = ''.join(self._fragments)
        return jinja2.Template(template).render(args)

    def params_values(self):
        return self._values

    def __repr__(self):
        return '{}({}): {}'.format(
            self._entry, self._count, repr(self._page_info)
        )
