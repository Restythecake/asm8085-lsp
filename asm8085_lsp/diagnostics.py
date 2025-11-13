"""
Diagnostics module for 8085 Assembly LSP.

This module handles diagnostic collection and publishing:
- Assembling code and collecting errors
- Converting assembler errors to LSP diagnostics
- Managing diagnostic state and caching
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Diagnostic:
    """
    Represents a single diagnostic (error, warning, etc).

    Attributes:
        line: Zero-based line number
        start_char: Start character position in line
        end_char: End character position in line
        severity: Diagnostic severity (1=error, 2=warning, 3=info, 4=hint)
        message: Human-readable diagnostic message
        source: Source of diagnostic (e.g., "asm8085")
        code: Optional diagnostic code
        tags: Optional diagnostic tags (1=unnecessary, 2=deprecated)
    """

    line: int
    start_char: int
    end_char: int
    severity: int
    message: str
    source: str = "asm8085"
    code: Optional[str] = None
    tags: Optional[List[int]] = None

    def to_lsp_dict(self) -> Dict:
        """
        Convert to LSP diagnostic dictionary.

        Returns:
            Dictionary in LSP diagnostic format.
        """
        diagnostic = {
            "range": {
                "start": {"line": self.line, "character": self.start_char},
                "end": {"line": self.line, "character": self.end_char},
            },
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
        }

        if self.code is not None:
            diagnostic["code"] = self.code

        if self.tags:
            diagnostic["tags"] = self.tags

        return diagnostic


class DiagnosticsCollector:
    """Collects and manages diagnostics for assembly files."""

    def __init__(self):
        """Initialize diagnostics collector."""
        self._cache: Dict[str, List[Diagnostic]] = {}

    def collect_from_assembly(
        self, uri: str, source_code: str
    ) -> Tuple[List[Diagnostic], Optional[Dict[str, int]]]:
        """
        Collect diagnostics by assembling the source code.

        Args:
            uri: Document URI
            source_code: Source code to assemble

        Returns:
            Tuple of (diagnostics list, label map or None)
        """
        from .asm8085_cli.assembler import assemble

        diagnostics: List[Diagnostic] = []
        lines = source_code.splitlines()

        try:
            # Attempt to assemble
            result = assemble(source_code)

            # Collect errors from assembly result
            for error in result.get("diagnostics", []):
                line_num = error.line_number or 1
                line_idx = max(0, line_num - 1)

                # Get line length for end position
                if line_idx < len(lines):
                    line_text = lines[line_idx]
                    end_char = len(line_text)
                else:
                    end_char = 100  # Fallback

                diagnostics.append(
                    Diagnostic(
                        line=line_idx,
                        start_char=0,
                        end_char=end_char,
                        severity=1,  # Error
                        message=error.message,
                    )
                )

            # Get label map for go-to-definition
            label_map = result.get("labels")

            return diagnostics, label_map

        except Exception as e:
            # Catch-all for unexpected errors
            diagnostics.append(
                Diagnostic(
                    line=0,
                    start_char=0,
                    end_char=100,
                    severity=1,  # Error
                    message=f"Assembly failed: {str(e)}",
                )
            )
            return diagnostics, None

    def get_cached(self, uri: str) -> Optional[List[Diagnostic]]:
        """
        Get cached diagnostics for a document.

        Args:
            uri: Document URI

        Returns:
            Cached diagnostics or None
        """
        return self._cache.get(uri)

    def update_cache(self, uri: str, diagnostics: List[Diagnostic]) -> None:
        """
        Update cached diagnostics for a document.

        Args:
            uri: Document URI
            diagnostics: New diagnostics list
        """
        self._cache[uri] = diagnostics

    def clear_cache(self, uri: str) -> None:
        """
        Clear cached diagnostics for a document.

        Args:
            uri: Document URI
        """
        self._cache.pop(uri, None)

    def to_lsp_format(self, diagnostics: List[Diagnostic]) -> List[Dict]:
        """
        Convert list of diagnostics to LSP format.

        Args:
            diagnostics: List of Diagnostic objects

        Returns:
            List of LSP diagnostic dictionaries
        """
        return [diag.to_lsp_dict() for diag in diagnostics]
