from typing import Callable, Mapping

import passpy.store


def github_auth_token_passpy(path) -> Callable[[], Mapping[str, str]]:
    def get_token(path: str) -> str:
        return passpy.store.Store().get_key(path).strip()

    return lambda: {"Authorization": "token " + get_token(path)}
