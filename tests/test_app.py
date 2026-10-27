import logging

import pytest
from fastapi import FastAPI
from observability.handler import OpenSearchHandler

import appinfo
from conftest import WEBHOOK_TOKEN

OPER_FEED_PATH = "/webhooks/tbank/oper-feed-operation"
PAYMENT_STATUS_PATH = "/webhooks/tbank/payment-status"
HEALTHCHECK_PATH = "/webhooks/tbank/healthcheck"

OPER_FEED_BODY = {
    "operationId": "op-1",
    "typeOfOperation": "Credit",
    "accountNumber": "40702810000000000001",
    "operationAmount": "1500.00",
    "operationCurrencyDigitalCode": "643",
    "counterParty": {"name": "Payer LLC", "inn": "7700000000"},
    "operationStatus": "transaction",
}
PAYMENT_STATUS_BODY = {"paymentId": "pay-1", "status": "EXECUTED", "description": "paid"}

pytestmark = pytest.mark.anyio


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_import_builds_the_app_with_the_token_from_the_environment(app_module):
    assert isinstance(app_module.app, FastAPI)
    assert app_module.WEBHOOK_TOKEN == WEBHOOK_TOKEN


def test_import_without_opensearch_settings_logs_to_stderr_only(app_module):
    handlers = logging.getLogger().handlers
    assert not any(isinstance(h, OpenSearchHandler) for h in handlers)


async def test_healthcheck_answers_with_name_and_version_through_trace_middleware(client):
    response = await client.get(HEALTHCHECK_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": appinfo.app_name,
        "version": appinfo.app_version,
    }
    assert response.headers["traceparent"].startswith("00-")


async def test_oper_feed_operation_with_the_right_token_is_accepted(client):
    response = await client.post(OPER_FEED_PATH, json=OPER_FEED_BODY, headers=bearer(WEBHOOK_TOKEN))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["operationId"] == "op-1"


async def test_payment_status_with_the_right_token_is_accepted(client):
    response = await client.post(PAYMENT_STATUS_PATH, json=PAYMENT_STATUS_BODY, headers=bearer(WEBHOOK_TOKEN))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["paymentId"] == "pay-1"


@pytest.mark.parametrize(
    ("path", "body"),
    [(OPER_FEED_PATH, OPER_FEED_BODY), (PAYMENT_STATUS_PATH, PAYMENT_STATUS_BODY)],
)
async def test_webhook_with_a_wrong_token_is_refused(client, path, body):
    response = await client.post(path, json=body, headers=bearer("wrong-token"))

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("path", "body"),
    [(OPER_FEED_PATH, OPER_FEED_BODY), (PAYMENT_STATUS_PATH, PAYMENT_STATUS_BODY)],
)
async def test_webhook_without_a_token_is_refused(client, path, body):
    response = await client.post(path, json=body)

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("path", "body", "required"),
    [(OPER_FEED_PATH, OPER_FEED_BODY, "operationId"), (PAYMENT_STATUS_PATH, PAYMENT_STATUS_BODY, "paymentId")],
)
async def test_webhook_missing_its_id_is_rejected(client, path, body, required):
    incomplete = {k: v for k, v in body.items() if k != required}

    response = await client.post(path, json=incomplete, headers=bearer(WEBHOOK_TOKEN))

    assert response.status_code == 422
