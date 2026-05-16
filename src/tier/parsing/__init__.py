"""AST parsing and schema validation for tool-call sequences.

The :class:`Parser` consumes raw model completions (in XML, JSON, or direct
formats) and returns a structured representation of the tool-call AST that
can be validated against function schemas and then executed against the
simulated environment.  :class:`ASTValidator` performs the schema-adherence
checks underlying TIER's :math:`R_{\\text{parse}}` reward component.
"""

from tier.parsing.ast_parser import Parser
from tier.parsing.validator import ASTValidator

__all__ = ["Parser", "ASTValidator"]
