import logging
import os

import appinfo
from dotenv import load_dotenv

# Load env vars FIRST so setup_logging() can read them
if os.getenv('container'):
    load_dotenv('/run/secrets/env')
else:
    load_dotenv('.env')

from observability import setup_logging, TraceMiddleware  # noqa: E402

setup_logging()

import json
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)

WEBHOOK_TOKEN = os.getenv("TBANK_WEBHOOK_TOKEN")

app = FastAPI(title=appinfo.app_name, version=appinfo.app_version)
app.add_middleware(TraceMiddleware)

security = HTTPBearer()


# Pydantic models
class CounterParty(BaseModel):
    account: Optional[str] = None
    bankBic: Optional[str] = None
    bankName: Optional[str] = None
    bankSwiftCode: Optional[str] = None
    corrAccount: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    name: Optional[str] = None

class Merch(BaseModel):
    id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    index: Optional[str] = None
    name: Optional[str] = None

class Receiver(BaseModel):
    account: Optional[str] = None
    name: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    bic: Optional[str] = None
    corrAccount: Optional[str] = None
    bankName: Optional[str] = None

class Payer(BaseModel):
    account: Optional[str] = None
    name: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    bic: Optional[str] = None
    corrAccount: Optional[str] = None
    bankName: Optional[str] = None

class OperFeedOperation(BaseModel):
    operationId: str
    typeOfOperation: Optional[str] = None
    accountNumber: Optional[str] = None
    documentNumber: Optional[str] = None
    operationAmount: Optional[str] = None
    operationCurrencyDigitalCode: Optional[str] = None
    accountAmount: Optional[str] = None
    accountCurrencyDigitalCode: Optional[str] = None
    rubleAmount: Optional[str] = None
    counterParty: Optional[CounterParty] = None
    description: Optional[str] = None
    authorizationDate: Optional[str] = None
    trxnPostDate: Optional[str] = None
    payVo: Optional[str] = None
    priority: Optional[str] = None
    cardNumber: Optional[str] = None
    ucid: Optional[str] = None
    mcc: Optional[str] = None
    merch: Optional[Merch] = None
    acquirerId: Optional[str] = None
    status: Optional[str] = None
    operationStatus: Optional[str] = None
    bic: Optional[str] = None
    rrn: Optional[str] = None
    category: Optional[str] = None
    payPurpose: Optional[str] = None
    receiver: Optional[Receiver] = None
    payer: Optional[Payer] = None
    drawDate: Optional[str] = None
    chargeDate: Optional[str] = None
    kbk: Optional[str] = None
    oktmo: Optional[str] = None
    taxEvidence: Optional[str] = None
    taxPeriod: Optional[str] = None
    taxDocNumber: Optional[str] = None
    taxDocDate: Optional[str] = None
    nalType: Optional[str] = None
    docDate: Optional[str] = None
    VO: Optional[str] = None

class PaymentStatus(BaseModel):
    paymentId: str
    status: Optional[str] = None
    description: Optional[str] = None


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != WEBHOOK_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


@app.post("/webhooks/tbank/oper-feed-operation")
async def tbank_oper_feed_operation(
    operation: OperFeedOperation,
    token: str = Depends(verify_token)
):
    """
    Handle incoming 'oper-feed-operation' webhooks from T-Bank.
    This endpoint receives notifications about new incoming payments on the company accounts.
    """
    try:
        operation_data = operation.model_dump(exclude_none=True)
        logger.info(
            "Received oper-feed-operation webhook",
            extra={
                "operation_id": operation.operationId,
                "type_of_operation": operation.typeOfOperation,
                "account_number": operation.accountNumber,
                "operation_amount": operation.operationAmount,
                "operation_currency": operation.operationCurrencyDigitalCode,
                "operation_status": operation.operationStatus,
                "operation": operation_data,
            }
        )
        return {
            "status": "success",
            "message": "'oper-feed-operation' webhook has been received and processed",
            "operationId": operation.operationId
        }
    except Exception as e:
        logger.error(
            "Error processing oper-feed-operation webhook",
            extra={"operation_id": operation.operationId},
            exc_info=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while processing 'oper-feed-operation' webhook"
        )


@app.post("/webhooks/tbank/payment-status")
async def tbank_payment_status(
    payment_status: PaymentStatus,
    token: str = Depends(verify_token)
):
    """
    Handle incoming 'payment-status' webhooks from T-Bank.
    This endpoint receives status updates on payments that were made via T-Bank API.
    """
    try:
        payment_data = payment_status.model_dump(exclude_none=True)
        logger.info(
            "Received payment-status webhook",
            extra={
                "payment_id": payment_status.paymentId,
                "payment_status": payment_status.status,
                "payment_description": payment_status.description,
                "payment": payment_data,
            }
        )
        return {
            "status": "success",
            "message": "'payment-status' webhook has been received and processed",
            "paymentId": payment_status.paymentId
        }
    except Exception as e:
        logger.error(
            "Error processing payment-status webhook",
            extra={"payment_id": payment_status.paymentId},
            exc_info=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while processing 'payment-status' webhook"
        )


@app.get("/webhooks/tbank/healthcheck")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": appinfo.app_name,
        "version": appinfo.app_version
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
