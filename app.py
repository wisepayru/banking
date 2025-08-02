import appinfo
import os
import json
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv('.env')

app = FastAPI(title=appinfo.app_name, version=appinfo.app_version)
security = HTTPBearer()

# load token from env
if os.getenv('container'):
    load_dotenv('/run/secrets/tbank-webhook-handler-secrets')
else:
    load_dotenv('.env')
WEBHOOK_TOKEN = os.getenv("TBANK_WEBHOOK_TOKEN")

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
    operationId: str  # Required field
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
    paymentId: str  # Required field
    status: Optional[str] = None
    description: Optional[str] = None

# auth dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != WEBHOOK_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@app.post("/tbank/oper-feed-operation")
async def tbank_oper_feed_operation(
    operation: OperFeedOperation,
    token: str = Depends(verify_token)
):
    """
    Handle incoming 'oper-feed-operation' webhooks from T-Bank.
    This endpoint receives notifications about new incoming payments on the company accounts.
    """
    try:
        # logging the validated operation data as JSON
        operation_json = operation.model_dump(exclude_none=True)
        print(f"[OPER-FEED-OPERATION] Received operation: {json.dumps(operation_json, indent=2, ensure_ascii=False)}")
        
        return {
            "status": "success",
            "message": "'oper-feed-operation' webhook has been received and processed",
            "operationId": operation.operationId
        }
    except Exception as e:
        print(f"[OPER-FEED-OPERATION] Error while processing 'oper-feed-operation' webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while processing 'oper-feed-operation' webhook"
        )

@app.post("/tbank/payment-status")
async def tbank_payment_status(
    payment_status: PaymentStatus,
    token: str = Depends(verify_token)
):
    """
    Handle incoming 'payment-status' webhooks from T-Bank.
    This endpoint receives status updates on payments that were made via T-Bank API.
    """
    try:
        # logging the validated payment status data as JSON
        payment_status_json = payment_status.model_dump(exclude_none=True)
        print(f"[PAYMENT-STATUS] Received status update: {json.dumps(payment_status_json, indent=2, ensure_ascii=False)}")
        
        return {
            "status": "success",
            "message": "'payment-status' webhook has been received and processed",
            "paymentId": payment_status.paymentId
        }
    except Exception as e:
        print(f"[PAYMENT-STATUS] Error while processing 'payment-status' webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while processing 'payment-status' webhook"
        )

@app.get("/healthcheck")
async def health_check():
    """Health check endpoint"""
    print(appinfo.name)
    return {
        "status": "healthy", 
        "service": appinfo.app_name,
        "version": appinfo.app_version
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)