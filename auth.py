import passpy.store

def github_auth_token_passpy(path):
    def get_token(path):
        return passpy.store.Store().get_key(path).strip()
    return lambda: {
        'Authorization': 'token ' + get_token(path)
    }
