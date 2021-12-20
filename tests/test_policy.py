from ghaudit.policy import perm_higher, perm_highest

# from hypothesis import given, strategies as st


def test_perm_higher() -> None:
    assert not perm_higher("admin", "admin")
    assert perm_higher("admin", "write")
    assert perm_higher("admin", "read")
    assert not perm_higher("write", "admin")
    assert not perm_higher("write", "write")
    assert perm_higher("write", "read")
    assert not perm_higher("read", "admin")
    assert not perm_higher("read", "write")
    assert not perm_higher("read", "read")


def test_perm_highest() -> None:
    assert perm_highest("admin", "admin") == "admin"
    assert perm_highest("admin", "write") == "admin"
    assert perm_highest("admin", "read") == "admin"
    assert perm_highest("admin", None) == "admin"
    assert perm_highest("write", "admin") == "admin"
    assert perm_highest("write", "write") == "write"
    assert perm_highest("write", "read") == "write"
    assert perm_highest("write", None) == "write"
    assert perm_highest("read", "admin") == "admin"
    assert perm_highest("read", "write") == "write"
    assert perm_highest("read", "read") == "read"
    assert perm_highest("read", None) == "read"
    assert perm_highest(None, "admin") == "admin"
    assert perm_highest(None, "write") == "write"
    assert perm_highest(None, "read") == "read"
