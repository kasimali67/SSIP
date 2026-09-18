import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.db import get_session
from app.models.audit_log import AuditLog
from app.schemas.ocr import OcrExtractResponse
from app.services.ocr_engine import extract_fields

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


async def require_profile_id(
    authorization: Annotated[str | None, Header()] = None,
) -> uuid.UUID:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured",
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a subject",
        )
    try:
        return uuid.UUID(str(subject))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is not a valid user id",
        ) from exc


@router.post("/extract", response_model=OcrExtractResponse)
async def extract_ocr(
    file: Annotated[UploadFile, File()],
    profile_id: Annotated[uuid.UUID, Depends(require_profile_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OcrExtractResponse:
    # TODO(rbac): restrict extraction to the owning authenticated user once the
    # role/permission layer lands.
    image_bytes = await file.read()
    await file.close()

    try:
        result = await run_in_threadpool(extract_fields, image_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image payload",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OCR provider unavailable",
        ) from exc

    session.add(
        AuditLog(
            profile_id=profile_id,
            action="ocr_extract",
            metadata_={
                "name_confidence": result.name.confidence,
                "dob_confidence": result.dob.confidence,
                "id_number_confidence": result.id_number.confidence,
            },
        )
    )
    await session.commit()
    return result
