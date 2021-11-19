from typing import cast
from typing import Optional
from typing import Mapping
from typing import MutableMapping
from typing import Collection
from typing_extensions import TypedDict


class RawDataEntry(TypedDict):
    email: str
    login: str


class RawData(TypedDict):
    map: Collection[RawDataEntry]


class MutableUserMap(TypedDict):
    by_login: MutableMapping[str, str]
    by_email: MutableMapping[str, str]


class UserMap(TypedDict):
    by_login: Mapping[str, str]
    by_email: Mapping[str, str]


def load(data: RawData) -> UserMap:
    usermap = {"by_login": {}, "by_email": {}}  # type: MutableUserMap
    for entry in data["map"]:
        login = entry["login"]
        email = entry["email"]
        if login in usermap["by_login"]:
            print("Error: duplicate login in usermap: {}".format(login))
        if email in usermap["by_login"]:
            print("Error: duplicate login in usermap: {}".format(login))
        usermap["by_login"][login] = email
        usermap["by_email"][email] = login
    return cast(UserMap, usermap)


def email(usermap: UserMap, login: str) -> Optional[str]:
    if login in usermap["by_login"]:
        return usermap["by_login"][login]
    return None


def login(usermap: UserMap, email: str) -> Optional[str]:
    if login in usermap["by_email"]:
        return usermap["by_email"][email]
    return None
