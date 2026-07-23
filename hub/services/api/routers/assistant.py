import os
from fastapi import APIRouter, HTTPException, status, Request
import sys

# Ensure import of shared types
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))
from shared.types.api_types import LLMQueryRequest, LLMQueryResponse, GenericResponseEnvelope

router = APIRouter()


@router.post("/assistant", response_model=GenericResponseEnvelope)
async def query_assistant(payload: LLMQueryRequest, request: Request):
    """
    Query the on-device AI Assistant.
    Retrieves recent sensor reading contexts from the database and runs RAG analysis.

    The assistant instance (and its shared DB pool) is owned by the application
    lifespan, so no per-request connection or model load happens here.
    """
    assistant = request.app.state.assistant
    try:
        res = await assistant.query(payload.prompt)
        data = LLMQueryResponse(
            response=res["response"],
            context_used=res["context_used"]
        )
        return GenericResponseEnvelope(data=data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running assistant prompt: {e}"
        )
