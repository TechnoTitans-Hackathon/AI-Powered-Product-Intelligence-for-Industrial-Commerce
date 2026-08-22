import asyncio
import json
import logging
import uuid
import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.core.db import SessionLocal
from backend.db.models import AITraceLog

logger = logging.getLogger(__name__)

TRACE_MAX_INLINE_BYTES = 50000  # 50KB

class TraceEvent(BaseModel):
    trace_id: str
    request_id: Optional[str] = None
    job_id: Optional[str] = None
    product_id: Optional[str] = None
    tenant_id: Optional[str] = None
    sequence: int = 0
    parent_event_id: Optional[str] = None
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    stage: str
    event_type: str
    component: Optional[str] = None
    status: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")


class TraceEmitter:
    """Singleton Trace Emitter for observing AI Pipeline."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TraceEmitter, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._subscribers: List[asyncio.Queue] = []
        self._persistence_queue = asyncio.Queue(maxsize=10000)
        self._sequence_counter: Dict[str, int] = {}
        self._sequence_lock = asyncio.Lock()
        
        # Start background worker lazily
        self._worker_task = None
        self._initialized = True
        logger.info("TraceEmitter initialized (worker will start on first emit).")

    async def get_next_sequence(self, trace_id: str) -> int:
        """Atomic sequence allocator per trace."""
        async with self._sequence_lock:
            current = self._sequence_counter.get(trace_id, 0)
            next_seq = current + 1
            self._sequence_counter[trace_id] = next_seq
            return next_seq

    def subscribe(self, maxsize: int = 1000) -> asyncio.Queue:
        """Returns a new subscriber queue."""
        q = asyncio.Queue(maxsize=maxsize)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    def _truncate_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Truncate large payloads to avoid bloating the DB."""
        if not payload:
            return payload
            
        payload_str = json.dumps(payload)
        original_size = len(payload_str.encode('utf-8'))
        
        if original_size > TRACE_MAX_INLINE_BYTES:
            return {
                "truncated": True,
                "original_size": original_size,
                "preview": payload_str[:200] + "... [TRUNCATED]",
                "message": "Payload exceeded maximum inline size."
            }
        return payload

    async def emit(self, event: TraceEvent):
        """Emit a trace event to subscribers and persistence."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._persistence_worker())
            logger.info("TraceEmitter worker started.")

        if not event.sequence:
            event.sequence = await self.get_next_sequence(event.trace_id)
            
        # Truncate payload for safe persistence and broadcasting
        event.payload = self._truncate_payload(event.payload)
        
        # 1. Fan-out to subscribers
        dead_queues = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"TraceEmitter: Subscriber queue full. Dropping event {event.event_id}")
            except Exception as e:
                dead_queues.append(q)
                
        for q in dead_queues:
            self.unsubscribe(q)
            
        # 2. Async Persistence
        try:
            self._persistence_queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.error(f"TraceEmitter: Persistence queue full. Dropping trace event {event.event_id}")

    async def _persistence_worker(self):
        """Background worker to save events to SQLite with independent sessions."""
        while True:
            try:
                # Get events in batches if possible
                events = []
                # Block for the first event
                events.append(await self._persistence_queue.get())
                
                # Try to get more events if available to batch them
                while not self._persistence_queue.empty() and len(events) < 50:
                    try:
                        events.append(self._persistence_queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break

                # Write batch using independent DB session
                db = SessionLocal()
                try:
                    for evt in events:
                        log_record = AITraceLog(
                            id=evt.event_id,
                            trace_id=evt.trace_id,
                            request_id=evt.request_id,
                            job_id=evt.job_id,
                            product_id=evt.product_id,
                            tenant_id=evt.tenant_id,
                            sequence=evt.sequence,
                            parent_event_id=evt.parent_event_id,
                            timestamp=evt.timestamp,
                            stage=evt.stage,
                            event_type=evt.event_type,
                            component=evt.component,
                            status=evt.status,
                            metrics_json=evt.metrics,
                            payload_json=evt.payload
                        )
                        db.add(log_record)
                        self._persistence_queue.task_done()
                        
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"TraceEmitter: Persistence failed: {e}")
                finally:
                    db.close()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"TraceEmitter: Worker error: {e}")
                await asyncio.sleep(1)  # backoff

trace_emitter = TraceEmitter()
