"""
Go-to-definition provider for 8085 Assembly LSP.

Provides navigation to label definitions.
"""

from typing import Dict, Optional


class DefinitionProvider:
    """Provides go-to-definition for labels."""

    def __init__(self):
        """Initialize definition provider."""
        self._label_lines: Dict[str, Dict[str, int]] = {}

    def update_labels(self, uri: str, label_map: Dict[str, int]) -> None:
        """
        Update label definitions for a document.

        Args:
            uri: Document URI
            label_map: Dictionary mapping label names to line numbers (0-based)
        """
        self._label_lines[uri] = {
            name.upper(): line for name, line in label_map.items()
        }

    def provide_definition(self, uri: str, word: str) -> Optional[Dict]:
        """
        Provide definition location for a symbol.

        Args:
            uri: Document URI
            word: Symbol under cursor

        Returns:
            LSP location or None
        """
        word_upper = word.upper()
        label_map = self._label_lines.get(uri, {})

        if word_upper in label_map:
            line = label_map[word_upper]
            return {
                "uri": uri,
                "range": {
                    "start": {"line": line, "character": 0},
                    "end": {"line": line, "character": 0},
                },
            }

        return None
