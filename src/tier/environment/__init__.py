"""DepthBench simulated environment.

The simulator exposes 163 hand-crafted APIs as attributes of
:class:`SimulatedAPIEnvironment`.  Each API class subclasses
:class:`APIBase` and exposes a single :meth:`execute` method that consumes
keyword arguments and returns either a structured result or a structured
error response.
"""

from tier.environment.api_base import API_base, APIBase
from tier.environment.simulator import SimulatedAPIEnvironment

__all__ = ["APIBase", "API_base", "SimulatedAPIEnvironment"]
