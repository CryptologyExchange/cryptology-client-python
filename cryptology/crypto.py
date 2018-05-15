import os
import os.path
import xdrlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from typing import Optional, Tuple
from . import internal
from .exceptions import InvalidKey

SIGNATURE_HASH = internal.SHA512()
SIGNATURE_PADDING = internal.PSS(
    mgf=internal.MGF1(SIGNATURE_HASH),
    salt_length=internal.PSS.MAX_LENGTH
)

ENCRYPTION_PADDING = internal.OAEP(
    mgf=internal.MGF1(algorithm=internal.SHA1()),
    algorithm=internal.SHA1(),
    label=None
)

BACKEND = default_backend()


class Cipher:
    __slots__ = ('key',)

    key: bytes

    def __init__(self, key: bytes) -> None:
        assert len(key) == 32
        self.key = key

    def encrypt(self, data: bytes) -> bytes:
        iv = os.urandom(16)
        padder = internal.PKCS7(internal.AES.block_size).padder()
        padded_data = padder.update(data) + padder.finalize()
        encryptor = internal.Cipher(internal.AES(self.key), internal.CBC(iv), BACKEND).encryptor()
        return iv + encryptor.update(padded_data) + encryptor.finalize()

    def decrypt(self, data: bytes) -> bytes:
        iv, cipherdata = data[:16], data[16:]
        decryptor = internal.Cipher(internal.AES(self.key), internal.CBC(iv), BACKEND).decryptor()
        plaintext_padded = decryptor.update(cipherdata)
        try:
            plaintext_padded += decryptor.finalize()
        except ValueError:
            raise InvalidKey()
        unpadder = internal.PKCS7(internal.AES.block_size).unpadder()

        unpadded = unpadder.update(plaintext_padded)
        try:
            unpadded += unpadder.finalize()
        except ValueError:
            raise InvalidKey()
        return unpadded


class Keys:
    __slots__ = ('public', 'private',)

    public: internal.RSAPublicKey
    private: Optional[internal.RSAPrivateKey]

    @staticmethod
    def load(public_filename: str, private_filename: Optional[str]) -> 'Keys':
        with open(public_filename, 'rb') as key_file:
            public_key = load_pem_public_key(
                key_file.read(),
                backend=BACKEND
            )

        private_key: Optional[internal.RSAPrivateKey] = None
        if private_filename:
            with open(private_filename, 'rb') as key_file:
                private_key = load_pem_private_key(
                    key_file.read(),
                    password=None,
                    backend=BACKEND
                )

        return Keys(public_key, private_key)

    def __init__(self, public: internal.RSAPublicKey, private: Optional[internal.RSAPrivateKey]) -> None:
        self.public = public
        self.private = private

    def sign(self, data: bytes) -> bytes:
        assert self.private is not None
        return self.private.sign(data, SIGNATURE_PADDING, SIGNATURE_HASH)

    def verify(self, signature: bytes, data: bytes) -> None:
        try:
            self.public.verify(signature, data, SIGNATURE_PADDING, SIGNATURE_HASH)
        except InvalidSignature:
            raise InvalidKey()

    def encrypt(self, data: bytes) -> bytes:
        return self.public.encrypt(data, ENCRYPTION_PADDING)

    def decrypt(self, data: bytes) -> bytes:
        assert self.private is not None
        try:
            return self.private.decrypt(data, ENCRYPTION_PADDING)
        except ValueError:
            raise InvalidKey()


def encrypt_and_sign(keys: Keys, cipher: Cipher, data: bytes) -> bytes:
    xdr = xdrlib.Packer()
    xdr.pack_bytes(keys.sign(data))
    xdr.pack_bytes(data)
    return cipher.encrypt(xdr.get_buffer())


def decrypt_and_verify(keys: Keys, cipher: Cipher, encrypted: bytes) -> Tuple[bytes, bytes]:
    raw = cipher.decrypt(encrypted)
    xdr = xdrlib.Unpacker(raw)
    signature = xdr.unpack_bytes()
    data = xdr.unpack_bytes()
    keys.verify(signature, data)
    return raw, data
