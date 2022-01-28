"""Miscellaneous routines."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Iterable, Mapping, Set, TypeVar, cast

import requests

from ghaudit.auth import AuthDriver

GITHUB_GRAPHQL_DEFAULT_ENDPOINT = "https://api.github.com/graphql"


# pylint: disable=too-few-public-methods
class LazyJsonFmt:
    """Lazy JSON formatter for logging.

    Defer the json.dumps operation of some arguments so that the formatting
    actually only happens if a logging operation is actually evaluated.
    """

    def __init__(self, argument: Any) -> None:
        self._argument = argument

    def __str__(self) -> str:
        return json.dumps(self._argument)


def github_graphql_call(
    call_str: str,
    auth_driver: AuthDriver,
    variables: Iterable[str],
    session: requests.Session | None,
    endpoint: str = GITHUB_GRAPHQL_DEFAULT_ENDPOINT,
) -> Mapping[str, Any]:
    """Make a GraphQL github API call."""
    logging.debug(
        'Github GraphQL query: "%s"',
        LazyJsonFmt({"query": call_str, "variables": json.dumps(variables)}),
    )
    if not session:
        session = requests.session()
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
            "github returned an error: {}".format(result["errors"])
        )
    return cast(Mapping[str, Any], result)


# pylint: disable=invalid-name
T = TypeVar("T")


def find_duplicates(
    sequence: Iterable[T],
    hash_func: Callable[[T], str] | None = None,
) -> Set[str]:
    if hash_func:
        hsequence = cast(Iterable[str], map(hash_func, sequence))
    else:
        hsequence = cast(Iterable[str], sequence)
    first_seen = set()  # type: Set[str]
    first_seen_add = first_seen.add
    return {i for i in hsequence if i in first_seen or first_seen_add(i)}
