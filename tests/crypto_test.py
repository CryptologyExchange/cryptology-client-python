import pytest

from cryptology import InvalidKey
from cryptology.crypto import Keys


def test_encryption() -> None:
    keys = Keys.load('./tests/server_test.pub', './tests/server_test.priv')
    encrypted_data = keys.encrypt(b'test')

    assert keys.decrypt(encrypted_data) == b'test'


def test_signing() -> None:
    keys = Keys.load('./tests/server_test.pub', './tests/server_test.priv')

    signature = keys.sign(b'test')

    keys.verify(signature, b'test')

    other_keys = Keys.load('./tests/client_test.pub', './tests/client_test.priv')
    other_signature = other_keys.sign(b'test')

    with pytest.raises(InvalidKey):
        assert keys.verify(other_signature, b'test')
