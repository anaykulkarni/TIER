"""System prompts, function-schema definitions, and sampling defaults.

Bundled with the package so they can be loaded via :mod:`importlib.resources`
without needing the source repository on disk.
"""

from importlib import resources
from pathlib import Path


def prompt_path(*parts: str) -> Path:
    """Return a filesystem path to a bundled prompt asset.

    Example:
        >>> prompt_path("instructions", "json.txt")
        PosixPath('.../tier/prompts/instructions/json.txt')
    """
    pkg_root = resources.files(__name__)
    return Path(str(pkg_root.joinpath(*parts)))


FUNCTION_DEFINITIONS = prompt_path("function_definitions.json")
FEWSHOT_EXAMPLES = prompt_path("fewshot_examples.txt")
SAMPLING_PARAMS = prompt_path("sampling_params.json")


def instructions(style: str) -> Path:
    """Resolve an instruction prompt by short name.

    Supported styles:
        ``"xml"`` (basic), ``"xml_chain"`` (multi-step XML),
        ``"xml_nochain"``, ``"json"`` (multi-step JSON, paper default),
        ``"json_nochain"``, ``"direct_nochain"``, ``"sft"``.
    """
    return prompt_path("instructions", f"{style}.txt")
