"""Compatibility module.

Settings now live in ``app.core.config``. This module re-exports them so that
existing imports of ``app.config`` keep working. New code should import from
``app.core.config`` directly.
"""
from app.core.config import (
    AppEnv,
    AuthMode,
    DigiLockerMode,
    Settings,
    get_settings,
)

__all__ = ["AppEnv", "AuthMode", "DigiLockerMode", "Settings", "get_settings"]
