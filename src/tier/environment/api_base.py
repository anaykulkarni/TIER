"""Common base class for every simulated API.

Each subclass implements :meth:`execute` and may load a CSV-backed data
table at construction time.  Errors are returned as plain dictionaries with
``status_code`` and ``error`` fields rather than raised, mirroring the shape
of a real HTTP response and keeping the reward signal deterministic.
"""

from __future__ import annotations

import os
from abc import ABC

import pandas as pd


class APIBase(ABC):
    """Abstract base class for all DepthBench / ToolACE / xLAM APIs."""

    def __init__(self, file_path: str | os.PathLike[str] | None = None):
        self.df = self.initialize_csv_data(file_path)

    def initialize_csv_data(
        self,
        file_path: str | os.PathLike[str] | None,
        required_columns: list[str] | None = None,
        **pandas_kwargs,
    ) -> pd.DataFrame:
        """Load a CSV-backed data table for the API.

        Args:
            file_path: Path to the CSV file.  May be ``None`` for APIs that
                do not read from disk (e.g., auto-generated ToolACE/xLAM
                stubs); in that case the method returns ``None``.
            required_columns: Columns whose presence to verify after loading.
            **pandas_kwargs: Extra arguments forwarded to :func:`pandas.read_csv`.
        """
        if file_path is None:
            return None

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"File not found: {file_path}. Please provide a valid file path."
            )

        try:
            df = pd.read_csv(file_path, **pandas_kwargs)
        except Exception as exc:
            raise ValueError(
                f"Invalid CSV format in file: {file_path}. Error: {exc}"
            ) from exc

        if required_columns:
            missing = [c for c in required_columns if c not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")

        return df

    def handle_error(self, error_msg: str = "Not found", error_code: int = 404) -> dict:
        """Return a structured error response with HTTP-style status code."""
        return {
            "status_code": error_code,
            "error": error_msg,
        }

    def validate_type(self, param, param_name: str, expected_type, custom_msg: str | None = None):
        """Type-check a parameter; return ``(ok, error_dict_or_None)``."""
        if not isinstance(param, expected_type):
            if custom_msg:
                msg = custom_msg
            else:
                if isinstance(expected_type, tuple):
                    expected = " or ".join(t.__name__ for t in expected_type)
                else:
                    expected = expected_type.__name__
                msg = (
                    f"Parameter '{param_name}' must be of type {expected}, "
                    f"got {type(param).__name__}"
                )
            return False, self.handle_error(msg, 422)
        return True, None

    def validate_param(self, condition: bool, error_msg: str, error_code: int = 400):
        """Generic predicate validation; returns ``(ok, error_dict_or_None)``."""
        if not condition:
            return False, self.handle_error(error_msg, error_code)
        return True, None


# Back-compat alias.  The auto-generated ToolACE and xLAM API files reference
# ``API_base`` (the original snake_case name); keeping the alias here means
# we do not have to touch tens of thousands of generated lines.
API_base = APIBase
