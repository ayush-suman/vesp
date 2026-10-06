import inspect
import pytest

def _view(obj, *keys: str):
    return (", ".join(keys), [
        tuple(case[key] for key in keys)
        for case in obj
    ])


def with_cases(case_list):
    def wrapper(fn):
        sig = inspect.signature(fn)
        return pytest.mark.parametrize(*_view(case_list, *sig.parameters))(fn)
    return wrapper
