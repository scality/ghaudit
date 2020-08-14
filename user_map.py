
def email(usermap, login):
    login_is = lambda x, y: 'login' in x and x['login'] == y
    elems = [x for x in usermap if login_is(x, login)]
    if not len(elems) <= 1:
        print(elems)
        assert len(elems) <= 1
    if elems:
        return elems[0]['email']
    return None
