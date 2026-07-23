import os
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg
import sys

# Ensure import of shared types
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))
from shared.types.api_types import NodeStatus, GenericResponseEnvelope
from hub.services.api.main import get_db

router = APIRouter()

@router.get("/nodes", response_model=GenericResponseEnvelope)
async def list_nodes(conn: asyncpg.Connection = Depends(get_db)):
    """
    List status of all registered sensor nodes.
    """
    rows = await conn.fetch("SELECT node_id, type, last_seen, firmware_version, status FROM nodes ORDER BY node_id ASC")
    nodes = []
    for r in rows:
        nodes.append(NodeStatus(
            node_id=r["node_id"],
            type=r["type"],
            last_seen=r["last_seen"],
            firmware_version=r["firmware_version"],
            status=r["status"]
        ))
    return GenericResponseEnvelope(data=nodes)

@router.get("/nodes/{node_id}", response_model=GenericResponseEnvelope)
async def get_node(node_id: str, conn: asyncpg.Connection = Depends(get_db)):
    """
    Retrieve status of a single sensor node by its unique ID.
    """
    row = await conn.fetchrow(
        "SELECT node_id, type, last_seen, firmware_version, status FROM nodes WHERE node_id = $1", 
        node_id
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found"
        )
    
    node = NodeStatus(
        node_id=row["node_id"],
        type=row["type"],
        last_seen=row["last_seen"],
        firmware_version=row["firmware_version"],
        status=row["status"]
    )
    return GenericResponseEnvelope(data=node)

@router.post("/nodes/{node_id}/ota", response_model=GenericResponseEnvelope)
async def trigger_ota(node_id: str, conn: asyncpg.Connection = Depends(get_db)):
    """
    Mock trigger OTA command publication for a target node.
    """
    # Check node exists
    exists = await conn.fetchval("SELECT COUNT(*) FROM nodes WHERE node_id = $1", node_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found"
        )

    # In final implementation: publish to MQTT "aurasense/nodes/{node_id}/ota/cmd"
    return GenericResponseEnvelope(
        data={"message": f"OTA update triggered for node {node_id}"}
    )
