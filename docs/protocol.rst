========
Protocol
========


Handshake
---------

Client sends encrypted (with cryptology pub key) the payload containing ``CLIENT ID``,
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

In response, server sends the payload, encrypted with a client pub key:

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

Finally, a client confirms key ownership by signing ``DATA TO SIGN`` with the private key:

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
rsa signature proving that the given message is authorized by the client. Aes is using
session scoped ``CLIENT AES KEY`` generated during handshake.
Payload is described in :doc:`/client_messages`.
An RPC message has a similar structure except that ``REQUEST_ID`` has to be unique only
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

Every server message has the following shape:


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
            \underbrace{\text{TRANSACTION ID}}_\text{HYPER}
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
            \underbrace{\text{ERROR_TYPE}}_\text{ENUM}
            \quad
            \underbrace{\text{MESSAGE}}_\text{BINARY}
        \Big]
    \end{gather*}

where ``MESSAGE TYPE`` determines payload type:

- MESSAGE payload
   ``TRANSACTION ID`` is an incremental (but not necessarily sequential) value indicating
   message order on server and used by the client to skip processed events on reconnect.
   ``TIMESTAMP`` indicates when a particular event happened on server.
   Payload is described in :doc:`/server_messages`.

- RPC payload
   The ``REQUEST_ID`` field in the ``RPC`` response messages has the same value as in the request.

- ERROR message
   Contains a text description of the error in recent client messages.
   Followed by disconnect with an error code.

- THROTTLING message
   Contains an integer amount of orders the client should postpone sending to keep up with the rate limit.
   If no action taken the connection will be terminated with error "rate limit".
   Followed by ``REQUEST ID`` and ``ORDER ID`` of the order affected the rate limit.

and ``ERROR_TYPE`` determines an error type:

- DUPLICATE_CLIENT_ORDER_ID error
    ``client_order_id`` must be a unique field for each order created.
    ``DUPLICATE_CLIENT_ORDER_ID`` means that ``client_order_id`` in the sent message is not unique.

- INVALID_PAYLOAD error
    All client messages must be in a valid JSON format and contain all the required fields.
    ``INVALID_PAYLOAD`` means that client sends an invalid JSON or any required parameter is not sent.

- UNKNOWN_ERROR error
    Any other errors.


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
