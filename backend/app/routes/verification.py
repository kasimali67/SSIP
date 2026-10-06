"""DigiLocker two-step verification.

POST /api/verification/digilocker/start     -> consent URL + single-use state
POST /api/verification/digilocker/complete  -> fetch official record, compare, return result

Nothing from the official record is persisted. The audit log receives only
per-field statuses. Pending states live in process memory with a 10-minute
TTL; with more than one worker, move this to Redis or a signed cookie.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.db import get_session
from app.models.audit_log import AuditLog
from app.schemas.verification import (
    CrossVerificationResponse,
    DigiLockerCompleteRequest,
    DigiLockerStartRequest,
    DigiLockerStartResponse,
    FieldComparisonOut,
)
from app.services.digilocker import (
    DigiLockerConfigError,
    DigiLockerError,
    get_digilocker_client,
)
from app.services.i18n import get_transliterator
from app.services.profiles import ensure_profile
from app.services.verification import CrossVerificationService, OcrFieldInput

router = APIRouter(prefix="/api/verification", tags=["verification"])

_PENDING_TTL_SECONDS = 600


@dataclass(frozen=True)
class _PendingAuthorization:
    user_id: str
    code_verifier: str
    document_type: str
    expires_at: float


_pending: dict[str, _PendingAuthorization] = {}


def _purge_expired() -> None:
    now = time.time()
    for state in [key for key, item in _pending.items() if item.expires_at < now]:
        del _pending[state]


def _mask_last4(last4: str | None) -> str | None:
    return f"XXXX-XXXX-{last4}" if last4 else None


@router.post("/digilocker/start", response_model=DigiLockerStartResponse)
async def start_digilocker(
    body: DigiLockerStartRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DigiLockerStartResponse:
    try:
        client = get_digilocker_client(settings)
    except DigiLockerConfigError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "DigiLocker is not configured on this server.") from exc

    _purge_expired()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    _pending[state] = _PendingAuthorization(user.id, verifier, body.document_type, time.time() + _PENDING_TTL_SECONDS)
    return DigiLockerStartResponse(
        authorization_url=client.authorization_url(state, challenge), state=state, is_sandbox=client.is_sandbox
    )


@router.post("/digilocker/complete", response_model=CrossVerificationResponse)
async def complete_digilocker(
    body: DigiLockerCompleteRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CrossVerificationResponse:
    pending = _pending.pop(body.state, None)  # single use, even on failure
    if pending is None or pending.expires_at < time.time() or pending.user_id != user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This verification link has expired. Start verification again.")

    try:
        client = get_digilocker_client(settings)
        record = await client.fetch_record(body.code, pending.code_verifier, "aadhaar")
    except DigiLockerError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "DigiLocker did not respond. Try again in a minute.") from exc

    service = CrossVerificationService(transliterator=get_transliterator(settings))
    outcome = await service.compare(
        name=OcrFieldInput(body.fields.name.value, body.fields.name.confidence),
        dob=OcrFieldInput(body.fields.dob.value, body.fields.dob.confidence),
        id_last4=OcrFieldInput(body.fields.id_last4.value, body.fields.id_last4.confidence),
        record=record,
    )

    await ensure_profile(session, user)
    session.add(
        AuditLog(
            profile_id=None if user.is_mock else user.id,
            action="digilocker_cross_verify",
            metadata_={
                "overall": outcome.overall.value,
                "fields": {item.field: item.status.value for item in outcome.fields},
                "sandbox": record.is_sandbox,
            },
        )
    )
    await session.commit()

    document_values = {
        "name": body.fields.name.value,
        "dob": body.fields.dob.value,
        "id_last4": _mask_last4(body.fields.id_last4.value),
    }
    official_values = {"name": record.name, "dob": record.dob, "id_last4": _mask_last4(record.id_last4)}
    return CrossVerificationResponse(
        overall=outcome.overall.value,
        fields=[
            FieldComparisonOut(
                field=item.field,  # type: ignore[arg-type]
                status=item.status.value,
                reason=item.reason.value,
                score=item.score,
                low_ocr_confidence=item.low_ocr_confidence,
                document_value=document_values[item.field],
                official_value=official_values[item.field],
            )
            for item in outcome.fields
        ],
        issuer=record.issuer,
        is_sandbox=record.is_sandbox,
    )
