"""DigiLocker adapter: one interface, two implementations.

Both implementations follow the same consent-based OAuth2 flow shape:
  1. authorization_url(state, code_challenge) -> where to send the citizen
  2. the citizen consents and is redirected back with ?code=...&state=...
  3. fetch_record(code, code_verifier, document_type) -> OfficialRecord

SandboxDigiLockerClient serves synthetic personas and is always marked
is_sandbox=True. LiveDigiLockerClient performs a standard OAuth2 + PKCE code
exchange; the document endpoint path and XML layout are config-driven and
MUST be confirmed against the partner API specification issued during
DigiLocker requester onboarding before going live.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from urllib.parse import urlencode

import httpx

from app.core.config import DigiLockerMode, Settings

DocumentType = Literal["aadhaar"]


class DigiLockerError(RuntimeError):
    """DigiLocker could not complete the request (network, auth, or data)."""


class DigiLockerConfigError(DigiLockerError):
    """Live mode is selected but required configuration is missing."""


@dataclass(frozen=True)
class OfficialRecord:
    name: str
    dob: str  # YYYY-MM-DD, or YYYY when only the year is on record
    gender: str | None
    id_last4: str
    document_type: DocumentType
    issuer: str
    is_sandbox: bool


class DigiLockerClient(Protocol):
    is_sandbox: bool

    def authorization_url(self, state: str, code_challenge: str) -> str: ...

    async def fetch_record(self, code: str, code_verifier: str, document_type: DocumentType) -> OfficialRecord: ...


# Synthetic personas for demos. Each one exercises a different verification outcome.
_SANDBOX_PERSONAS: dict[str, OfficialRecord] = {
    "match": OfficialRecord("Ramesh Kumar Patel", "1985-08-15", "M", "4821", "aadhaar", "UIDAI (sandbox)", True),
    "spelling_variant": OfficialRecord("Ramesh K. Patel", "1985-08-15", "M", "4821", "aadhaar", "UIDAI (sandbox)", True),
    "dob_mismatch": OfficialRecord("Ramesh Kumar Patel", "1986-08-15", "M", "4821", "aadhaar", "UIDAI (sandbox)", True),
}
SANDBOX_CODE_PREFIX = "sandbox:"


class SandboxDigiLockerClient:
    is_sandbox = True

    def __init__(self, consent_url: str) -> None:
        self._consent_url = consent_url

    def authorization_url(self, state: str, code_challenge: str) -> str:
        return f"{self._consent_url}?{urlencode({'state': state})}"

    async def fetch_record(self, code: str, code_verifier: str, document_type: DocumentType) -> OfficialRecord:
        persona = code.removeprefix(SANDBOX_CODE_PREFIX) if code.startswith(SANDBOX_CODE_PREFIX) else ""
        record = _SANDBOX_PERSONAS.get(persona)
        if record is None:
            raise DigiLockerError("invalid_authorization_code")
        return record


class LiveDigiLockerClient:
    is_sandbox = False

    def __init__(self, settings: Settings) -> None:
        required = {
            "DIGILOCKER_CLIENT_ID": settings.digilocker_client_id,
            "DIGILOCKER_CLIENT_SECRET": settings.digilocker_client_secret,
            "DIGILOCKER_AUTHORIZE_URL": settings.digilocker_authorize_url,
            "DIGILOCKER_TOKEN_URL": settings.digilocker_token_url,
            "DIGILOCKER_API_BASE": settings.digilocker_api_base,
            "DIGILOCKER_EAADHAAR_PATH": settings.digilocker_eaadhaar_path,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise DigiLockerConfigError(f"Missing DigiLocker settings: {', '.join(missing)}")
        self._settings = settings

    def authorization_url(self, state: str, code_challenge: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._settings.digilocker_client_id,
            "redirect_uri": self._settings.digilocker_redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self._settings.digilocker_authorize_url}?{urlencode(params)}"

    async def fetch_record(self, code: str, code_verifier: str, document_type: DocumentType) -> OfficialRecord:
        s = self._settings
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                token_response = await client.post(
                    s.digilocker_token_url,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": s.digilocker_redirect_uri,
                        "client_id": s.digilocker_client_id,
                        "client_secret": s.digilocker_client_secret,
                        "code_verifier": code_verifier,
                    },
                )
                token_response.raise_for_status()
                access_token = token_response.json()["access_token"]
                document_response = await client.get(
                    f"{s.digilocker_api_base.rstrip('/')}/{s.digilocker_eaadhaar_path.lstrip('/')}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                document_response.raise_for_status()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise DigiLockerError(type(exc).__name__) from exc
        return parse_eaadhaar_xml(document_response.text)


def parse_eaadhaar_xml(xml_text: str) -> OfficialRecord:
    """Map an eAadhaar XML document to OfficialRecord.

    VERIFY element and attribute names against the DigiLocker partner spec.
    defusedxml blocks entity-expansion and external-entity attacks.
    """
    from defusedxml import ElementTree

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise DigiLockerError("unparseable_document") from exc

    poi = next((el for el in root.iter() if el.tag.endswith("Poi")), None)
    uid_holder = next((el for el in root.iter() if el.tag.endswith("UidData")), None)
    if poi is None or uid_holder is None:
        raise DigiLockerError("unexpected_document_layout")

    raw_dob = poi.get("dob", "")
    try:
        dob = datetime.strptime(raw_dob, "%d-%m-%Y").date().isoformat()  # noqa: DTZ007
    except ValueError:
        dob = raw_dob  # year-only records are compared as such downstream

    uid = "".join(ch for ch in uid_holder.get("uid", "") if ch.isdigit())
    if len(uid) < 4:
        raise DigiLockerError("missing_reference_digits")

    return OfficialRecord(
        name=poi.get("name", ""),
        dob=dob,
        gender=poi.get("gender"),
        id_last4=uid[-4:],
        document_type="aadhaar",
        issuer="UIDAI via DigiLocker",
        is_sandbox=False,
    )


def get_digilocker_client(settings: Settings) -> DigiLockerClient:
    if settings.digilocker_mode is DigiLockerMode.LIVE:
        return LiveDigiLockerClient(settings)
    return SandboxDigiLockerClient(consent_url=settings.sandbox_consent_url)
