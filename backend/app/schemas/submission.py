"""Pydantic schemas for the automated submission worker."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CitizenPayload(BaseModel):
    """Verified citizen data forwarded from the chat front-end."""

    name: str = Field(min_length=1, max_length=200)
    dob: str = Field(
        min_length=6,
        max_length=20,
        description="Date of birth as a string (e.g. 15/08/1985 or 1985-08-15).",
    )
    address: str = Field(default="", max_length=500)
    # The UID is intentionally accepted but never logged in plain text.
    aadhaar_last4: str | None = Field(
        default=None,
        pattern=r"^\d{4}$",
        description="Last 4 digits of Aadhaar — used only for form pre-fill.",
    )


class SubmissionRequest(BaseModel):
    """Full request body for POST /api/v1/submission/execute."""

    citizen: CitizenPayload
    # Optional: portal URL override for testing different environments.
    portal_url: str = Field(
        default="http://localhost:3000/mock-uidai.html",
        description="Target portal URL that Playwright will open.",
    )


class SubmissionResult(BaseModel):
    """Outcome returned to the chat after the Playwright worker completes."""

    success: bool
    urn: str | None = None          # Update Request Number scraped from portal
    screenshot_b64: str | None = None  # Base-64 PNG of final page state
    error: str | None = None
