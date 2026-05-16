"""Compatibility shim — re-exports :class:`APIBase` from :mod:`tier.environment.api_base`.

The auto-generated ToolACE per-tool modules use ``from .api_base import API_base``
(relative import).  Routing through this shim keeps one source of truth for the
base class while leaving the auto-generated files untouched.
"""

from tier.environment.api_base import API_base, APIBase  # noqa: F401
