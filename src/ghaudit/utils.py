import json
import logging
from typing import Callable, Iterable

import requests

GITHUB_GRAPHQL_DEFAULT_ENDPOINT = "https://api.github.com/graphql"


# pylint: disable=too-few-public-methods
class LazyJsonFmt:
    def __init__(self, argument):
        self._argument = argument

    def __str__(self):
        return json.dumps(self._argument)


def github_graphql_call(
    call_str: str,
    auth_driver: Callable[[], str],
    variables: Iterable[str],
    session: requests.Session = requests.session(),
    endpoint=GITHUB_GRAPHQL_DEFAULT_ENDPOINT,
) -> str:
    logging.debug(
        'Github GraphQL query: "%s"',
        LazyJsonFmt({"query": call_str, "variables": json.dumps(variables)}),
    )
    result_raw = session.post(
        endpoint,
        json={"query": call_str, "variables": json.dumps(variables)},
        headers=auth_driver(),
    )
    if result_raw.status_code != 200:
        error_fmt = (
            "Call failed to run by returning code of {}."
            "Error message: {}."
            "Query: {}"
        )
        raise Exception(
            error_fmt.format(
                result_raw.status_code, result_raw.text, call_str[:200]
            )
        )

    result = result_raw.json()
    if "errors" in result:
        raise RuntimeError(
            "github returned an error: {}".format(result["error"])
        )
    return result
