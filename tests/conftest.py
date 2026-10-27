import importlib
import socket
import sys

import httpx
import pytest

WEBHOOK_TOKEN = "test-webhook-token"


def _refuse_connect(self, address):
    raise AssertionError(f"tests must not open network connections, attempted {address!r}")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _refuse_connect)


@pytest.fixture(scope="session")
def app_module(tmp_path_factory):
    # app reads its settings once at import, so the environment is set before the import and restored after it.
    # the empty OpenSearch settings keep setup_logging on a stderr handler, and load_dotenv never overrides a
    # variable that is already set; the empty working directory leaves it no .env to read either
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(socket.socket, "connect", _refuse_connect)
        mp.chdir(tmp_path_factory.mktemp("cwd"))
        mp.delenv("container", raising=False)
        mp.setenv("TBANK_WEBHOOK_TOKEN", WEBHOOK_TOKEN)
        mp.setenv("OPENSEARCH_HOST", "")
        mp.setenv("OPENSEARCH_PASSWORD", "")
        sys.modules.pop("app", None)
        module = importlib.import_module("app")
    return module


@pytest.fixture
async def client(app_module):
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
