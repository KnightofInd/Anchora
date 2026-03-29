import hashlib
import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class IdempotencyService:
    """Stores and replays responses for idempotent write requests."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def build_request_hash(self, payload: dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    async def get_replay(
        self,
        *,
        user_id: str,
        endpoint: str,
        key: str,
        request_hash: str,
    ) -> tuple[int, dict[str, Any]] | None:
        result = await self.db.execute(
            text(
                """
                SELECT request_hash, status_code, response_body
                FROM idempotency_keys
                WHERE user_id = :user_id
                  AND endpoint = :endpoint
                  AND idem_key = :idem_key
                """
            ),
            {"user_id": user_id, "endpoint": endpoint, "idem_key": key},
        )
        row = result.mappings().first()
        if row is None:
            return None

        if row["request_hash"] != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key was already used with a different request payload.",
            )

        return int(row["status_code"]), dict(row["response_body"] or {})

    async def save(
        self,
        *,
        user_id: str,
        endpoint: str,
        key: str,
        request_hash: str,
        status_code: int,
        response_body: dict[str, Any],
    ) -> None:
        await self.db.execute(
            text(
                """
                INSERT INTO idempotency_keys (
                    user_id,
                    endpoint,
                    idem_key,
                    request_hash,
                    status_code,
                    response_body
                ) VALUES (
                    :user_id,
                    :endpoint,
                    :idem_key,
                    :request_hash,
                    :status_code,
                    CAST(:response_body AS JSONB)
                )
                ON CONFLICT (user_id, endpoint, idem_key) DO NOTHING
                """
            ),
            {
                "user_id": user_id,
                "endpoint": endpoint,
                "idem_key": key,
                "request_hash": request_hash,
                "status_code": status_code,
                "response_body": json.dumps(response_body, ensure_ascii=True),
            },
        )