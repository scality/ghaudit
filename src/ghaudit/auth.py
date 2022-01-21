"""Authentication drivers."""

from typing import Callable, Mapping

import passpy.store

AuthDriver = Callable[[], Mapping[str, str]]


def github_auth_token_passpy(path: str) -> AuthDriver:
    """Return a pass auth driver.

    Return a callback providing token authentication to github, given the path
    of a secret in pass, the GnuPG-based password manager.
    """

    def get_token(path: str) -> str:
        token = passpy.store.Store().get_key(path)
        if not token:
            raise RuntimeError("{} not found.".format(path))
        return token.strip()

    return lambda: {"Authorization": "token " + get_token(path)}
