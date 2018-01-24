========
Protocol
========


Handshake
---------

Client sends encrypted (with cryptology pub key) payload containing ``CLIENT ID``,
``LAST SEEN ORDER`` and ``CLIENT AES KEY``. aes key is random and session scoped:

.. math::
    \scriptsize
    \Longrightarrow
    \text{RSA ENCRYPT}
    \Bigg[
       \text{XDR}
       \Big[
           \underbrace{\text{CLIENT ID}}_\text{BINARY}
           \quad
           \underbrace{\text{LAST SEEN ORDER}}_\text{HYPER}
           \quad
           \underbrace{\text{CLIENT AES KEY}}_\text{BINARY}
       \Big]
    \Bigg]

In response, server sends payload, encrypted with client pub key:

.. math::
    \scriptsize
    \Longleftarrow
    \text{RSA ENCRYPT}
    \Bigg[
        \text{XDR}
        \Big[
            \underbrace{\text{DATA TO SIGN}}_\text{BINARY}
            \quad
            \underbrace{\text{LAST SEEN SEQUENCE}}_\text{HYPER}
            \quad
            \underbrace{\text{SERVER AES KEY}}_\text{BINARY}
        \Big]
    \Bigg]

Finally, client confirms key ownership by signing ``DATA TO SIGN`` with private key:

.. math::
    \scriptsize
    \Longrightarrow
    \text{RSA SIGN}
    \Bigg[
        \text{DATA TO SIGN}
    \Bigg]


Messages
--------

There are two types of client messages: Request Messages and RPC Messages.
The type is determined by the ``MESSAGE TYPE`` field.
Every request message includes ``SEQUENCE``, sequential value starting
from ``LAST SEEN SEQUENCE`` provided by server during handshake. It also has
rsa signature proving that given message is authorized by client. Aes is using
session scoped ``CLIENT AES KEY`` generated during handshake.
Payload is described in :doc:`/client_messages`.
A RPC message has similar structure except that ``REQUEST_ID`` has to be unique only
during current RPC request execution. The corresponding RPC response contains
the same ``REQUEST_ID`` as a reference.

.. math::
    \scriptsize
    \begin{gather*}
        \Longrightarrow
        \text{AES IV}
        \quad
        \text{AES}
        \Bigg[
            \text{XDR}
            \bigg[
                \underbrace{
                    \text{RSA SIGNATURE}
                    \Big[
                        \text{DATA}
                    \Big]
                }_\text{BINARY}
                \quad
                \underbrace{\text{MESSAGE TYPE}}_\text{ENUM}
                \quad
                \underbrace{\text{DATA}}_\text{BINARY}
            \bigg]
        \Bigg]
    \\
    \text{MESSAGE DATA} =
        \text{XDR}
        \Big[
            \underbrace{\text{SEQUENCE}}_\text{HYPER}
            \quad
            \underbrace{\text{JSON MESSAGE}}_\text{BINARY}
        \Big]
    \\
    \text{RPC DATA} =
        \text{XDR}
        \Big[
            \underbrace{\text{REQUEST_ID}}_\text{HYPER}
            \quad
            \underbrace{\text{JSON MESSAGE}}_\text{BINARY}
        \Big]
    \end{gather*}

Every sever message has the following shape:


.. math::
    \scriptsize
    \begin{gather*}
        \Longleftarrow
        \text{AES IV}
        \quad
        \text{AES}
        \Bigg[
            \text{XDR}
            \Big[
                \underbrace{\text{MESSAGE TYPE}}_\text{ENUM}
                \quad
                \underbrace{\text{DATA}}_\text{BINARY}
            \Big]
        \Bigg]
    \\
    \text{MESSAGE DATA} =
        \text{XDR}
        \Big[
            \underbrace{\text{ORDER}}_\text{HYPER}
            \quad
            \underbrace{\text{TIMESTAMP}}_\text{DOUBLE}
            \quad
            \underbrace{\text{JSON MESSAGE}}_\text{BINARY}
        \Big]
    \\
    \text{RPC DATA} =
        \text{XDR}
        \Big[
            \underbrace{\text{REQUEST_ID}}_\text{HYPER}
            \quad
            \underbrace{\text{JSON MESSAGE}}_\text{BINARY}
        \Big]
    \\
    \text{ERROR_MESSAGE} =
        \text{XDR}
        \Big[
            \underbrace{\text{MESSAGE}}_\text{BINARY}
        \Big]
    \end{gather*}

where ``MESSAGE TYPE`` determines payload type:

- MESSAGE payload
   ``ORDER`` is incremental (but not necessarily sequential) value indicating
   message order on server and used by client to skip processed events on reconnect.
   ``TIMESTAMP`` indicates when particular event happened on server.
   Payload is described in :doc:`/server_messages`.

- RPC payload
   The ``REQUEST_ID`` field in the ``RPC`` response messages has the same value as in the request.

- ERROR message
   Contains text description of the error in recent client messages.
   Followed by disconnect with error code.

Server also sends heartbeat messages (single zero byte) every 2 seconds, so client
can decide if connection is still alive.


Cryptography
------------

1. RSA
    .. code-block:: python3

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


3. AES
    padding: ``PKCS7``

    mode: ``CBC``
