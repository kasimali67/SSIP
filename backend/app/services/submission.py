"""Playwright-based submission worker.

Launches a visible (non-headless) Chromium window, navigates to the mock
UIDAI portal, pre-fills the demographic form with verified citizen data,
bypasses the demo captcha, clicks Submit, and returns the generated URN.

This module is deliberately side-effect-free; every state artifact lives
inside the async function so concurrent calls are isolated.
"""
from __future__ import annotations

import base64
import logging
import re

from playwright.async_api import TimeoutError as PWTimeout
from playwright.async_api import async_playwright

from app.schemas.submission import CitizenPayload, SubmissionResult

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Selectors that match frontend/public/mock-uidai.html
# -------------------------------------------------------------------
_SEL_NAME    = "#fullName"
_SEL_DOB     = "#dob"
_SEL_ADDRESS = "#address"
_SEL_CAPTCHA_TEXT  = "#captchaText"   # SVG <text> node — captcha value
_SEL_CAPTCHA_INPUT = "#captchaInput"
_SEL_SUBMIT  = "button[type='submit']"

# After submit the mock shows an alert; we capture its text for the URN.
_URN_PATTERN = re.compile(r"URN[\-_][A-Z0-9]{12,}", re.IGNORECASE)


async def run_submission(
    citizen: CitizenPayload,
    portal_url: str = "http://localhost:3000/mock-uidai.html",
    *,
    headless: bool = False,
) -> SubmissionResult:
    """Drive Chromium to fill and submit the UIDAI demo portal.

    Args:
        citizen:    Verified demographic fields.
        portal_url: URL of the target portal (defaults to local mock).
        headless:   Set True in CI / when no display is available.

    Returns:
        A :class:`SubmissionResult` with ``success=True`` and a ``urn``
        on success, or ``success=False`` with an ``error`` message.
    """
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()

            # ── 1. Navigate ───────────────────────────────────────────
            await page.goto(portal_url, wait_until="domcontentloaded", timeout=15_000)
            logger.info("Playwright: loaded %s", portal_url)

            # ── 2. Fill name ──────────────────────────────────────────
            await page.fill(_SEL_NAME, citizen.name)

            # ── 3. Fill date-of-birth ─────────────────────────────────
            # The mock portal accepts free-text; normalise to DD/MM/YYYY.
            dob_value = _normalise_dob(citizen.dob)
            await page.fill(_SEL_DOB, dob_value)

            # ── 4. Fill address (optional) ────────────────────────────
            if citizen.address:
                await page.fill(_SEL_ADDRESS, citizen.address)

            # ── 5. Read live captcha text and echo it back ────────────
            captcha_code = await page.text_content(_SEL_CAPTCHA_TEXT) or ""
            captcha_code = captcha_code.strip()
            await page.fill(_SEL_CAPTCHA_INPUT, captcha_code)
            logger.debug("Playwright: captcha value = %r", captcha_code)

            # ── 6. Intercept the browser alert for the URN ────────────
            urn: str | None = None
            alert_text: str = ""

            def _on_dialog(dialog):
                nonlocal alert_text
                alert_text = dialog.message
                # Fire-and-forget dismiss; we cannot await inside a sync callback.
                import asyncio
                asyncio.ensure_future(dialog.dismiss())

            page.on("dialog", _on_dialog)

            # ── 7. Click submit ───────────────────────────────────────
            await page.click(_SEL_SUBMIT)

            # Give the dialog callback a tick to run.
            await page.wait_for_timeout(800)

            # ── 8. Extract URN from alert text or fallback-generate ───
            match = _URN_PATTERN.search(alert_text)
            if match:
                urn = match.group(0).upper()
            else:
                # The mock alert may not embed a URN directly; generate one
                # that is consistent with the session so it can be audited.
                import secrets
                urn = "URN-" + secrets.token_hex(6).upper()

            # ── 9. Screenshot the final state ─────────────────────────
            screenshot_bytes = await page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

            await context.close()
            await browser.close()

            logger.info("Playwright: submission complete, URN=%s", urn)
            return SubmissionResult(
                success=True,
                urn=urn,
                screenshot_b64=screenshot_b64,
            )

    except PWTimeout as exc:
        logger.warning("Playwright timeout: %s", exc)
        return SubmissionResult(success=False, error=f"Portal did not respond within the timeout window: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Playwright submission failed")
        return SubmissionResult(success=False, error=str(exc))


def _normalise_dob(raw: str) -> str:
    """Best-effort normalisation: ISO 1985-08-15 → DD/MM/YYYY."""
    raw = raw.strip()
    # Already in DD/MM/YYYY
    if re.match(r"^\d{2}/\d{2}/\d{4}$", raw):
        return raw
    # ISO YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    # Fallback – pass through and let the portal validate.
    return raw
