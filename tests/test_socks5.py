import pytest

from socksio import (
    ProtocolError,
    SOCKS5AType,
    SOCKS5AuthMethod,
    SOCKS5AuthReply,
    SOCKS5Command,
    SOCKS5Connection,
    SOCKS5Reply,
    SOCKS5ReplyCode,
)
from socksio.socks5 import SOCKS5State
from socksio.utils import AddressType


@pytest.mark.parametrize(
    "atype,expected",
    [
        (AddressType.IPV4, SOCKS5AType.IPV4_ADDRESS),
        (AddressType.IPV6, SOCKS5AType.IPV6_ADDRESS),
        (AddressType.DN, SOCKS5AType.DOMAIN_NAME),
    ],
)
def test_socks5atype_from_address_type(
    atype: AddressType, expected: SOCKS5AType
) -> None:
    assert SOCKS5AType.from_atype(atype) == expected


def test_socks5atype_unknown_address_type_raises() -> None:
    with pytest.raises(ValueError):
        SOCKS5AType.from_atype("FOOBAR")  # type: ignore


def test_socks5_auth_request() -> None:
    conn = SOCKS5Connection()
    auth_methods = [SOCKS5AuthMethod.GSSAPI, SOCKS5AuthMethod.USERNAME_PASSWORD]

    conn.authenticate(auth_methods)

    data = conn.data_to_send()
    assert len(data) == 4
    assert data[0:1] == b"\x05"
    assert data[1:2] == len(auth_methods).to_bytes(1, byteorder="big")
    assert data[2:3] == SOCKS5AuthMethod.GSSAPI
    assert data[3:] == SOCKS5AuthMethod.USERNAME_PASSWORD


@pytest.mark.parametrize(
    "auth_method",
    [
        SOCKS5AuthMethod.NO_AUTH_REQUIRED,
        SOCKS5AuthMethod.USERNAME_PASSWORD,
        SOCKS5AuthMethod.GSSAPI,
    ],
)
def test_socks5_auth_reply_accepted(auth_method: SOCKS5AuthMethod) -> None:
    conn = SOCKS5Connection()
    request_methods = [
        SOCKS5AuthMethod.NO_AUTH_REQUIRED,
        SOCKS5AuthMethod.USERNAME_PASSWORD,
        SOCKS5AuthMethod.GSSAPI,
    ]

    conn.authenticate(request_methods)
    reply = conn.receive_data(b"\x05" + auth_method)

    assert reply == SOCKS5AuthReply(method=auth_method)


def test_socks5_auth_reply_no_acceptable_auth_method() -> None:
    conn = SOCKS5Connection()
    conn.authenticate([SOCKS5AuthMethod.USERNAME_PASSWORD])
    reply = conn.receive_data(b"\x05\xFF")

    assert reply == SOCKS5AuthReply(method=SOCKS5AuthMethod.NO_ACCEPTABLE_METHODS)


@pytest.mark.parametrize(
    "data", [b"\x05", b"\x05\x10"]  # missing method byte , incorrect method value
)
def test_socks5_auth_reply_malformed(data: bytes) -> None:
    conn = SOCKS5Connection()
    conn.authenticate([SOCKS5AuthMethod.USERNAME_PASSWORD])
    with pytest.raises(ProtocolError):
        conn.receive_data(data)


def test_socks5_auth_username_password_requires_connect_waiting() -> None:
    conn = SOCKS5Connection()
    with pytest.raises(ProtocolError):
        conn.authenticate_username_password(b"username", b"password")


def test_socks5_auth_username_password_success() -> None:
    conn = SOCKS5Connection()
    conn.authenticate([SOCKS5AuthMethod.USERNAME_PASSWORD])
    conn.data_to_send()
    conn.receive_data(b"\x05" + SOCKS5AuthMethod.USERNAME_PASSWORD)
    conn.authenticate_username_password(b"username", b"password")
    assert conn.data_to_send() == b"\x01\x08username\x08password"
    conn.receive_data(b"\x00")
    assert conn.state == SOCKS5State.CLIENT_AUTHENTICATED


def test_socks5_auth_username_password_fail() -> None:
    conn = SOCKS5Connection()
    conn.authenticate([SOCKS5AuthMethod.USERNAME_PASSWORD])
    conn.data_to_send()
    conn.receive_data(b"\x05" + SOCKS5AuthMethod.USERNAME_PASSWORD)
    conn.authenticate_username_password(b"username", b"password")
    assert conn.data_to_send() == b"\x01\x08username\x08password"
    conn.receive_data(b"\x01")
    assert conn.state == SOCKS5State.MUST_CLOSE


def test_socks5_request_require_authentication() -> None:
    conn = SOCKS5Connection()
    with pytest.raises(ProtocolError):
        conn.request(SOCKS5Command.CONNECT, addr="127.0.0.1", port=1080)


@pytest.fixture
def authenticated_conn() -> SOCKS5Connection:
    conn = SOCKS5Connection()
    conn.authenticate([SOCKS5AuthMethod.USERNAME_PASSWORD])
    conn.data_to_send()
    conn.receive_data(b"\x05" + SOCKS5AuthMethod.USERNAME_PASSWORD)
    conn.authenticate_username_password(b"username", b"password")
    conn.data_to_send()
    conn.receive_data(b"\x00")
    return conn


@pytest.mark.parametrize("command", (SOCKS5Command.CONNECT, SOCKS5Command.BIND))
def test_socks5_request_ipv4(
    authenticated_conn: SOCKS5Connection, command: SOCKS5Command
) -> None:
    authenticated_conn.request(command, addr="127.0.0.1", port=1080)

    data = authenticated_conn.data_to_send()

    assert len(data) == 10
    assert data[0:1] == b"\x05"
    assert data[1:2] == command
    assert data[2:3] == b"\x00"
    assert data[3:4] == b"\x01"
    assert data[4:8] == b"\x7f\x00\x00\x01"
    assert data[8:] == (1080).to_bytes(2, byteorder="big")


@pytest.mark.parametrize("command", (SOCKS5Command.CONNECT, SOCKS5Command.BIND))
def test_socks5_request_domain_name(
    authenticated_conn: SOCKS5Connection, command: SOCKS5Command
) -> None:
    authenticated_conn.request(command, addr="localhost", port=1080)

    data = authenticated_conn.data_to_send()

    assert len(data) == 15
    assert data[0:1] == b"\x05"
    assert data[1:2] == command
    assert data[2:3] == b"\x00"
    assert data[3:4] == b"\x03"
    assert data[4:13] == b"localhost"
    assert data[13:] == (1080).to_bytes(2, byteorder="big")


@pytest.mark.parametrize("command", (SOCKS5Command.CONNECT, SOCKS5Command.BIND))
def test_socks5_request_ipv6(
    authenticated_conn: SOCKS5Connection, command: SOCKS5Command
) -> None:
    authenticated_conn.request(command, addr="0:0:0:0:0:0:0:1", port=1080)

    data = authenticated_conn.data_to_send()

    assert len(data) == 22
    assert data[0:1] == b"\x05"
    assert data[1:2] == command
    assert data[2:3] == b"\x00"
    assert data[3:4] == b"\x04"
    assert (
        data[4:20]
        == b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
    )
    assert data[20:] == (1080).to_bytes(2, byteorder="big")


@pytest.mark.parametrize(
    "atype,addr,expected_atype,expected_addr",
    [
        (b"\x01", b"\x7f\x00\x00\x01", SOCKS5AType.IPV4_ADDRESS, "127.0.0.1"),
        (b"\x03", b"localhost", SOCKS5AType.DOMAIN_NAME, "localhost"),
        (
            b"\x04",
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
            SOCKS5AType.IPV6_ADDRESS,
            "::1",
        ),
    ],
)
def test_socks5_reply_success(
    authenticated_conn: SOCKS5Connection,
    atype: bytes,
    addr: bytes,
    expected_atype: SOCKS5AType,
    expected_addr: str,
) -> None:
    data = b"".join(
        [
            b"\x05",  # protocol version
            b"\x00",  # reply
            b"\x00",  # reserved
            atype,
            addr,
            (1080).to_bytes(2, byteorder="big"),  # port
        ]
    )
    reply = authenticated_conn.receive_data(data)

    assert authenticated_conn.state == SOCKS5State.TUNNEL_READY
    assert reply == SOCKS5Reply(
        reply_code=SOCKS5ReplyCode.SUCCEEDED,
        atype=expected_atype,
        addr=expected_addr,
        port=1080,
    )


@pytest.mark.parametrize(
    "data",
    [
        b"\x00\x00\x00\x01\x7f\x00\x00\x01\x048",  # incorrect protocol version
        b"\x05\x00\x00\x01\x7f\x00\x00\x01\x04",  # missing one byte of port number
        b"\x05\x00\x00\x01\x7f\x00\x00\x048",  # missing one byte of address
    ],
)
def test_socks5_receive_malformed_data(
    authenticated_conn: SOCKS5Connection, data: bytes
) -> None:
    with pytest.raises(ProtocolError):
        authenticated_conn.receive_data(data)


@pytest.mark.parametrize("error_code", list(SOCKS5ReplyCode)[1:])
@pytest.mark.parametrize(
    "atype,addr,expected_atype,expected_addr",
    [
        (b"\x01", b"\x7f\x00\x00\x01", SOCKS5AType.IPV4_ADDRESS, "127.0.0.1"),
        (b"\x03", b"localhost", SOCKS5AType.DOMAIN_NAME, "localhost"),
        (
            b"\x04",
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
            SOCKS5AType.IPV6_ADDRESS,
            "::1",
        ),
    ],
)
def test_socks5_reply_error(
    error_code: SOCKS5ReplyCode,
    authenticated_conn: SOCKS5Connection,
    atype: bytes,
    addr: bytes,
    expected_atype: SOCKS5AType,
    expected_addr: str,
) -> None:
    data = b"".join(
        [
            b"\x05",  # protocol version
            error_code,
            b"\x00",  # reserved
            atype,
            addr,
            (1080).to_bytes(2, byteorder="big"),  # port
        ]
    )
    reply = authenticated_conn.receive_data(data)

    assert authenticated_conn.state == SOCKS5State.MUST_CLOSE
    assert reply == SOCKS5Reply(
        reply_code=error_code, atype=expected_atype, addr=expected_addr, port=1080
    )
