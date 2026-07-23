import os
import uuid
import sys
from fastapi import APIRouter, HTTPException, status

# Ensure import of shared types
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))
from shared.types.api_types import PairRequest, PairResponse, GenericResponseEnvelope
from hub.services.api.security import verify_pairing_code, issue_token

router = APIRouter()


@router.post("/pair", response_model=GenericResponseEnvelope)
async def pair(req: PairRequest):
    """
    Exchange the hub's out-of-band pairing code for a short-lived bearer token.

    This endpoint is intentionally unauthenticated — it is how a client bootstraps
    a token. In D2 the static pairing code is replaced by the BLE/QR provisioning
    flow, but the token issuance/verification here stays the same.
    """
    if not verify_pairing_code(req.pairing_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid pairing code",
        )
    client_id = req.client_name or f"client-{uuid.uuid4().hex[:8]}"
    token, expires_at = issue_token(client_id)
    return GenericResponseEnvelope(
        data=PairResponse(access_token=token, expires_at=expires_at, client_id=client_id)
    )
