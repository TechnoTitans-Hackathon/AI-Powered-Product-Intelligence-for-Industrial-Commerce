from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import json

from backend.core.db import get_db
from backend.core.auth import get_current_user
from backend.db.models import User, AITraceLog
from ai_engine.tracing.emitter import trace_emitter

router = APIRouter()

@router.get("/recent")
def get_recent_traces(
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    after_sequence: Optional[int] = Query(None, description="Only fetch events strictly after this sequence"),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> List[Any]:
    """Fetch historical trace events to hydrate UI or recover from disconnect."""
    # Note: Admin role check could be added here if defined in the schema
    
    query = db.query(AITraceLog)
    
    if trace_id:
        query = query.filter(AITraceLog.trace_id == trace_id)
    if job_id:
        query = query.filter(AITraceLog.job_id == job_id)
    if product_id:
        query = query.filter(AITraceLog.product_id == product_id)
    if after_sequence is not None:
        query = query.filter(AITraceLog.sequence > after_sequence)
        
    query = query.order_by(AITraceLog.timestamp.desc(), AITraceLog.sequence.desc()).limit(limit)
    
    events = query.all()
    # Reverse to return chronological order
    events = reversed(events)
    
    return [
        {
            "event_id": e.id,
            "trace_id": e.trace_id,
            "request_id": e.request_id,
            "job_id": e.job_id,
            "product_id": e.product_id,
            "tenant_id": e.tenant_id,
            "sequence": e.sequence,
            "parent_event_id": e.parent_event_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "stage": e.stage,
            "event_type": e.event_type,
            "component": e.component,
            "status": e.status,
            "metrics": e.metrics_json or {},
            "payload": e.payload_json or {}
        }
        for e in events
    ]


@router.get("/stream")
async def stream_traces(
    request: Request,
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    after_sequence: Optional[int] = Query(None, description="Ignore events up to this sequence"),
    user: User = Depends(get_current_user)
):
    """Server-Sent Events (SSE) stream for Live AI Pipeline Traces."""
    
    async def event_generator():
        q = trace_emitter.subscribe()
        try:
            # Heartbeat loop + queue reading
            while True:
                # If client disconnects
                if await request.is_disconnected():
                    break
                    
                try:
                    # Wait for an event with a timeout for heartbeat
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    
                    # Filtering logic
                    if trace_id and event.trace_id != trace_id:
                        continue
                        
                    if trace_id and after_sequence is not None and event.sequence <= after_sequence:
                        continue
                        
                    # Format as SSE
                    data_str = json.dumps({
                        "event_id": event.event_id,
                        "trace_id": event.trace_id,
                        "request_id": event.request_id,
                        "job_id": event.job_id,
                        "product_id": event.product_id,
                        "tenant_id": event.tenant_id,
                        "sequence": event.sequence,
                        "parent_event_id": event.parent_event_id,
                        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                        "stage": event.stage,
                        "event_type": event.event_type,
                        "component": event.component,
                        "status": event.status,
                        "metrics": event.metrics,
                        "payload": event.payload,
                    })
                    
                    yield f"id: {event.event_id}\nevent: trace_event\ndata: {data_str}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send a comment as a heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
                    
        finally:
            trace_emitter.unsubscribe(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
