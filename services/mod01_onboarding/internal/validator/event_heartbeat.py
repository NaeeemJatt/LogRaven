"""Event stream telemetry heartbeat validator (FR-MOD1-04)."""

import asyncio
import json
import time
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import ClientError


class EventHeartbeatValidator:
    """Sends and verifies test telemetry heartbeat through regional EventBus / Event Hub."""

    def __init__(self, events_client: Optional[Any] = None):
        self._events_client = events_client

    def _get_events_client(self, session_credentials: Optional[Dict[str, Any]] = None):
        if self._events_client is not None:
            return self._events_client
        if session_credentials:
            return boto3.client(
                "events",
                aws_access_key_id=session_credentials.get("access_key_id"),
                aws_secret_access_key=session_credentials.get("secret_access_key"),
                aws_session_token=session_credentials.get("session_token"),
            )
        return boto3.client("events")

    async def verify_event_stream(
        self,
        event_bus_arn: str,
        tenant_id: str,
        session_credentials: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 10.0,
    ) -> Dict[str, Any]:
        """Dispatches probe event and validates successful delivery within timeout budget."""
        events = self._get_events_client(session_credentials)
        probe_entry = {
            "Source": "lograven.probe",
            "DetailType": "HeartbeatProbe",
            "Detail": json.dumps({
                "tenant_id": tenant_id,
                "timestamp": int(time.time()),
                "probe": "SYN_ACK",
            }),
            "EventBusName": event_bus_arn,
        }

        try:
            start = time.perf_counter()
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    events.put_events,
                    Entries=[probe_entry],
                ),
                timeout=timeout_seconds,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            failed_count = response.get("FailedEntryCount", 0)

            if failed_count == 0:
                return {
                    "healthy": True,
                    "latency_ms": round(elapsed_ms, 2),
                    "event_bus_arn": event_bus_arn,
                }
            else:
                entries = response.get("Entries", [])
                err_code = entries[0].get("ErrorCode", "UnknownError") if entries else "FailedEntries"
                return {
                    "healthy": False,
                    "latency_ms": round(elapsed_ms, 2),
                    "error": err_code,
                    "event_bus_arn": event_bus_arn,
                }
        except asyncio.TimeoutError:
            return {
                "healthy": False,
                "error": "Probe timed out after 10 seconds",
                "event_bus_arn": event_bus_arn,
            }
        except ClientError as e:
            err_msg = e.response.get("Error", {}).get("Message", str(e))
            return {
                "healthy": False,
                "error": err_msg,
                "event_bus_arn": event_bus_arn,
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "event_bus_arn": event_bus_arn,
            }

