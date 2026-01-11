from typing import Callable
from functools import wraps

def assertion_wrapper(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AssertionError as ae:
            print(f"[ASSERTION] {ae}")
            return False

    return wrapper

def assert_1( condition: bool, msg: str ) -> None:
    if not condition:
        raise AssertionError( msg )