
from typing import Optional
from typing import Mapping
from typing import Collection

def email(usermap: Collection[Mapping[str, str]], login: str) -> Optional[str]:
    def login_filter(entry, login: str) -> bool:
        return 'login' in entry and entry['login'] == login
    elems = [x for x in usermap if login_filter(x, login)]
    if not len(elems) <= 1:
        print(elems)
        assert len(elems) <= 1
    if elems:
        return elems[0]['email']
    return None

def login(usermap: Collection[Mapping[str, str]], email: str) -> Optional[str]:
    elems = [x for x in usermap if 'email' in x and x['email'] == email]
    if not len(elems) <= 1:
        print(elems)
        assert len(elems) <= 1
    if elems:
        return elems[0]['login']
    return None
