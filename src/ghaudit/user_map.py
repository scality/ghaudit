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
        new_login = entry["login"]
        new_email = entry["email"]
        if new_login in usermap["by_login"]:
            print("Error: duplicate login in usermap: {}".format(new_login))
        if new_email in usermap["by_login"]:
            print("Error: duplicate login in usermap: {}".format(new_login))
        usermap["by_login"][new_login] = new_email
        usermap["by_email"][new_email] = new_login
    return cast(UserMap, usermap)


def email(usermap: UserMap, user_login: str) -> Optional[str]:
    if user_login in usermap["by_login"]:
        return usermap["by_login"][user_login]
    return None


def login(usermap: UserMap, user_email: str) -> Optional[str]:
    if user_email in usermap["by_email"]:
        return usermap["by_email"][user_email]
    return None
