"""Compatibility shim — re-exports :class:`APIBase` from :mod:`tier.environment.api_base`.

See ``data/toolace/toolace_apis/api_base.py`` for the rationale.
"""

from tier.environment.api_base import API_base, APIBase  # noqa: F401
