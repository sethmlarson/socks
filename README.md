# SOCKSIO

[![Build Status](https://travis-ci.org/sethmlarson/socksio.svg?branch=master)](https://travis-ci.org/sethmlarson/socksio)
[![codecov](https://codecov.io/gh/sethmlarson/socksio/branch/master/graph/badge.svg)](https://codecov.io/gh/sethmlarson/socksio)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/socksio.svg)](https://pypi.org/project/socksio)
[![PyPI](https://img.shields.io/pypi/v/socksio.svg)](https://pypi.org/project/socksio)

Client-side sans-I/O SOCKS proxy implementation.
Supports SOCKS4, SOCKS4A, and SOCKS5.

`socksio` is a sans-I/O library similar to
[`h11`](https://github.com/python-hyper/h11) or
[`h2`](https://github.com/python-hyper/hyper-h2/), this means the library itself
does not handle the actual sending of the bytes through the network, it only
deals with the implementation details of the SOCKS protocols so you can use
it in any I/O library you want.

## Current status: alpha

The API is not final and may be subject to change.

Features not yet implemented:

- SOCKS5 GSS-API authentication.
- SOCKS5 UDP associate requests.

## Usage

TL;DR check the [examples directory](examples/).

Being sans-I/O means that in order to test `socksio` you need an I/O library.
And the most basic I/O is, of course, the standard library's `socket` module.

You'll need to know ahead of time the type of SOCKS proxy you want to connect
to. Assuming we have a SOCKS4 proxy running in our machine on port 8080, we
will first create a connection to it:

```python
import socket

sock = socket.create_connection(("localhost", 8080))
```

`socksio` exposes modules for SOCKS4, SOCKS4A and SOCKS5, each of them includes
a `Connection` class:

```python
from socksio import socks4

# The SOCKS4 protocol requires a `user_id` to be supplied.
conn = socks4.SOCKS4Connection(user_id=b"socksio")
```

Since `socksio` is a sans-I/O library, we will use the socket to send and
receive data to our SOCKS4 proxy. The raw data, however, will be created and
parsed by our `SOCKS4Connection`.

We need to tell our connection we want to make a request to the proxy:

```python
# SOCKS4 does not allow domain names, below is an IP for google.com
conn.request(socks4.SOCKS4Command.CONNECT, "216.58.204.78", 80)
```

`socksio` exposes the possible SOCKS4 commands, we choose `CONNECT` and
specify the IP address and port we want to connect to.

The `SOCKS4Connection` will then compose the necessary `bytes` in the proper
format for us to send to our proxy:

```python
data = conn.data_to_send()
sock.sendall(data)
```

If all goes well the proxy will have sent reply, we just need to read from the
socket and pass the data to the `SOCKS4Connection`:

```python
data = sock.recv(1024)
event = conn.receive_data(data)
```

The connection will parse the data and return an event from it, in this case, a
`SOCKS4Reply` that includes attributes for the fields in the SOCKS reply:

```python
if event.reply_code != socks4.SOCKS4ReplyCode.REQUEST_GRANTED:
    raise Exception(
        "Server could not connect to remote host: {}".format(event.reply_code)
    )
```

If all went well the connection has been established correctly and we can
start sending our request directly to the proxy:

```python
sock.sendall(b"GET / HTTP/1.1\r\nhost: google.com\r\n\r\n")
data = receive_data(sock)
print(data)
# b'HTTP/1.1 301 Moved Permanently\r\nLocation: http://www.google.com/...`
```

The same methodology is used for all protocols, check out the
[examples directory](examples/) for more information.

## Development

Install the test requirements with `pip install -r test-requirements.txt`.

Install the project in pseudo-editable mode with `flit install -s`.

Tests can be ran directly invoking `pytest`.

This project uses [`nox`](https://nox.thea.codes/en/stable/) to automate
testing and linting tasks. `nox` is installed as part of the test requirements.
Invoking `nox` will run all sessions, but you may also run only some them, for
example `nox -s lint` will only run the linting session.

## Reference documents

Each implementation follows the documents as listed below:

- SOCKS4: https://www.openssh.com/txt/socks4.protocol
- SOCKS4A: https://www.openssh.com/txt/socks4a.protocol
- SOCKS5: https://www.ietf.org/rfc/rfc1928.txt
- SOCKS5 username/password authentication: https://www.ietf.org/rfc/rfc1929.txt
- SOCKS5 GSS-API authentication: https://www.ietf.org/rfc/rfc1961.txt

## License

MIT
