class SubQuery:
    def __init__(self):
        self._page_info = None
        self._count = 0

    def render(self, args):
        raise NotImplementedError("abstract function call")

    def entry(self):
        raise NotImplementedError("abstract function call")

    def params(self):
        raise NotImplementedError("abstract function call")

    def get_page_info(self):
        return self._page_info

    def update_page_info(self, response):
        raise NotImplementedError("abstract function call")

    def params_values(self):
        raise NotImplementedError("abstract function call")
