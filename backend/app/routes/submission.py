"""Submission automation route.

POST /api/v1/submission/execute
    Receives verified citizen data from the chat interface and triggers
    the Playwright worker to auto-fill and submit the mock UIDAI portal.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, get_current_user
from app.schemas.submission import SubmissionRequest, SubmissionResult
from app.services.submission import run_submission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/submission", tags=["submission"])


@router.post(
    "/execute",
    response_model=SubmissionResult,
    summary="Execute automated portal submission",
    description=(
        "Triggers the Playwright worker to navigate to the configured portal, "
        "pre-fill the demographic form with the verified citizen data, bypass "
        "the demo captcha, click Submit, and return the generated URN."
    ),
)
async def execute_submission(
    body: SubmissionRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> SubmissionResult:
    """Drive the browser worker and return the submission outcome."""
    logger.info(
        "Submission requested by user=%s portal=%s",
        user.id,
        body.portal_url,
    )

    result = await run_submission(
        citizen=body.citizen,
        portal_url=body.portal_url,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error or "Submission worker returned no error detail.",
        )

    return result
