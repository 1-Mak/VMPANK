import httpx
import pytest

from vpnctl.marzban import GB, MarzbanClient, MarzbanError


def make_client(handler):
    transport = httpx.MockTransport(handler)
    return MarzbanClient("http://127.0.0.1:8000", "admin", "pw", transport=transport)


def test_login_and_create_user():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/admin/token":
            return httpx.Response(200, json={"access_token": "tok"})
        if request.url.path == "/api/user" and request.method == "POST":
            seen["auth"] = request.headers.get("Authorization")
            import json

            body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "username": body["username"],
                    "status": "active",
                    "data_limit": body["data_limit"],
                    "used_traffic": 0,
                    "expire": body["expire"],
                    "subscription_url": "/sub/x",
                },
            )
        return httpx.Response(404)

    with make_client(handler) as client:
        user = client.create_user("alice", inbound_tag="vless-reality-in", data_limit_gb=5)
    assert seen["auth"] == "Bearer tok"
    assert user.data_limit == 5 * GB
    assert user.username == "alice"


def test_login_failure_raises():
    def handler(request):
        return httpx.Response(401, text="bad creds")

    with pytest.raises(MarzbanError):
        make_client(handler).login()


def test_reauth_on_401_then_succeeds():
    calls = {"list": 0, "login": 0}

    def handler(request):
        if request.url.path == "/api/admin/token":
            calls["login"] += 1
            return httpx.Response(200, json={"access_token": f"tok{calls['login']}"})
        if request.url.path == "/api/users":
            calls["list"] += 1
            if calls["list"] == 1:
                return httpx.Response(401, text="expired")
            return httpx.Response(200, json={"users": [{"username": "bob", "status": "active"}]})
        return httpx.Response(404)

    client = make_client(handler)
    client.login()
    users = client.list_users()
    assert calls["login"] == 2  # повторный логин после 401
    assert users[0].username == "bob"
