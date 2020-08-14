
def email(usermap, login):
    def login_filter(entry, login):
        return 'login' in entry and entry['login'] == login
    elems = [x for x in usermap if login_filter(x, login)]
    if not len(elems) <= 1:
        print(elems)
        assert len(elems) <= 1
    if elems:
        return elems[0]['email']
    return None
