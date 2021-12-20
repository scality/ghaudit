import json
import logging
from typing import Any, Iterable, Mapping

import requests

from ghaudit.auth import AuthDriver

GITHUB_GRAPHQL_DEFAULT_ENDPOINT = "https://api.github.com/graphql"


# pylint: disable=too-few-public-methods
class LazyJsonFmt:
    def __init__(self, argument: Any) -> None:
        self._argument = argument

    def __str__(self) -> str:
        return json.dumps(self._argument)


def github_graphql_call(
    call_str: str,
    auth_driver: AuthDriver,
    variables: Iterable[str],
    session: requests.Session = requests.session(),
    endpoint: str = GITHUB_GRAPHQL_DEFAULT_ENDPOINT,
) -> Mapping[str, Any]:
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
