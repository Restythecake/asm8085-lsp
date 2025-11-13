"""
Document symbols provider for 8085 Assembly LSP.

Provides document outline showing all labels in the file.
"""

from typing import Dict, List


class SymbolsProvider:
    """Provides document symbols (labels) for outline view."""

    def __init__(self):
        """Initialize symbols provider."""
        self._label_cache: Dict[str, List[Dict]] = {}

    def update_labels(self, uri: str, source_lines: List[str]) -> None:
        """
        Update symbols by parsing labels from source code.

        Args:
            uri: Document URI
            source_lines: List of source code lines
        """
        symbols = []

        for line_idx, line in enumerate(source_lines):
            # Look for label definitions (ends with colon)
            stripped = line.strip()
            if stripped and ":" in stripped:
                # Extract label name (before colon)
                label_part = stripped.split(":")[0].strip()

                # Skip if it's not a valid label (has spaces, etc)
                if " " not in label_part and label_part:
                    symbols.append(
                        {
                            "name": label_part,
                            "kind": 13,  # Variable/constant kind
                            "range": {
                                "start": {"line": line_idx, "character": 0},
                                "end": {
                                    "line": line_idx,
                                    "character": len(stripped),
                                },
                            },
                            "selectionRange": {
                                "start": {"line": line_idx, "character": 0},
                                "end": {
                                    "line": line_idx,
                                    "character": len(label_part),
                                },
                            },
                        }
                    )

        self._label_cache[uri] = symbols

    def provide_symbols(self, uri: str) -> List[Dict]:
        """
        Provide document symbols for a file.

        Args:
            uri: Document URI

        Returns:
            List of LSP document symbols
        """
        return self._label_cache.get(uri, [])
