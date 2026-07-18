import os
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg
import sys

# Ensure import of shared types
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))
from shared.types.api_types import LLMQueryRequest, LLMQueryResponse, GenericResponseEnvelope
from hub.services.llm_assistant import LLMAssistant
from hub.services.api.main import get_db

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aurasense")
router = APIRouter()

# Instantiate assistant wrapper
assistant = LLMAssistant(db_url=DATABASE_URL)

@router.post("/assistant", response_model=GenericResponseEnvelope)
async def query_assistant(request: LLMQueryRequest):
    """
    Query the on-device AI Assistant. 
    Retrieves recent sensor reading contexts from the database and runs RAG analysis.
    """
    try:
        res = await assistant.query(request.prompt)
        # Wrap response
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
