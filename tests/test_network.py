from roo.network import session_with_proxy


def test_network_no_proxy():
    session = session_with_proxy(None)
    assert session.proxies == {}
    assert session.trust_env


def test_network_with_proxy():
    session = session_with_proxy("http://example.com")
    assert session.proxies == {
        "http": "http://example.com",
        "https": "http://example.com"
    }
    assert not session.trust_env


def test_network_with_proxy_false():
    session = session_with_proxy(False)
    assert session.proxies == {}
    assert not session.trust_env
