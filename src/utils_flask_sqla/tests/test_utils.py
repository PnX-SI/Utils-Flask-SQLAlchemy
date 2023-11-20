import pytest
from utils_flask_sqla.utils import dict_merge, is_uuid


@pytest.fixture(scope="function")
def test_uuid_test():
    uuid = "772fbbe3-bde4-40fd-8b38-aa0cd55b9eb2"
    assert is_uuid(uuid)


def test_dict_merge(scope="function"):
    dict_ = {"b": {"a": 1}}
    dict_2 = {"b": {"a": 2}}
    dict_merge(dict_, dict_2)
    assert dict_["b"]["a"] == 2
