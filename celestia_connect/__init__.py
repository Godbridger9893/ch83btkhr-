"""Celestia Connect subsystem.

This package adds the local gateway, device registry, pairing flow, and
protocol definitions used by Celestia to reach companion devices.
"""

from .service import CelestiaConnectService, get_service

__all__ = ["CelestiaConnectService", "get_service"]
