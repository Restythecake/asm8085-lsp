"""
LSP Protocol implementation for JSON-RPC communication.

This module handles low-level protocol details:
- Reading/writing JSON-RPC messages over stdin/stdout
- Message serialization/deserialization
- Protocol constants and types
"""

import json
import sys
from typing import Any, Dict, Optional


class LSPProtocol:
    """Handles JSON-RPC message reading and writing over stdio."""

    def __init__(self):
        """Initialize the protocol handler."""
        self._message_count = 0

    def read_message(self) -> Optional[Dict[str, Any]]:
        """
        Read a single JSON-RPC message from stdin.

        Returns:
            Parsed message dictionary, or None if stream ended.

        Message format:
            Content-Length: N\r\n
            \r\n
            {JSON content}
        """
        try:
            # Read headers
            headers = {}
            while True:
                line = sys.stdin.buffer.readline().decode("utf-8")
                if not line or line in ("\r\n", "\n"):
                    break

                if ": " in line:
                    key, value = line.strip().split(": ", 1)
                    headers[key] = value

            # Check for required Content-Length header
            if "Content-Length" not in headers:
                return None

            # Read content
            content_length = int(headers["Content-Length"])
            content = sys.stdin.buffer.read(content_length).decode("utf-8")

            # Parse JSON
            message = json.loads(content)
            self._message_count += 1

            return message

        except (EOFError, ValueError, KeyError) as e:
            # Clean shutdown on stream end or malformed message
            return None

    def write_message(self, message: Dict[str, Any]) -> None:
        """
        Write a JSON-RPC message to stdout.

        Args:
            message: Message dictionary to send.

        Message format:
            Content-Length: N\r\n
            \r\n
            {JSON content}
        """
        try:
            # Ensure jsonrpc field is present
            if "jsonrpc" not in message:
                message["jsonrpc"] = "2.0"

            # Serialize message
            content = json.dumps(message, ensure_ascii=False)
            content_bytes = content.encode("utf-8")

            # Write with headers
            response = f"Content-Length: {len(content_bytes)}\r\n\r\n{content}"
            sys.stdout.buffer.write(response.encode("utf-8"))
            sys.stdout.buffer.flush()

        except (IOError, ValueError) as e:
            # Silently ignore write errors (client may have disconnected)
            pass

    def write_notification(self, method: str, params: Dict[str, Any]) -> None:
        """
        Write a notification (message without id).

        Args:
            method: Notification method name.
            params: Notification parameters.
        """
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        self.write_message(message)

    def write_response(self, msg_id: Any, result: Any) -> None:
        """
        Write a successful response.

        Args:
            msg_id: Request id to respond to.
            result: Response result.
        """
        message = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }
        self.write_message(message)

    def write_error(
        self, msg_id: Any, code: int, message: str, data: Any = None
    ) -> None:
        """
        Write an error response.

        Args:
            msg_id: Request id to respond to.
            code: Error code.
            message: Error message.
            data: Optional error data.
        """
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data

        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": error,
        }
        self.write_message(response)


# LSP Error Codes (from specification)
class ErrorCodes:
    """Standard JSON-RPC and LSP error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # LSP-specific
    SERVER_NOT_INITIALIZED = -32002
    UNKNOWN_ERROR_CODE = -32001
    REQUEST_CANCELLED = -32800
    CONTENT_MODIFIED = -32801


# LSP Message Types (for window/logMessage and window/showMessage)
class MessageType:
    """LSP message type constants."""

    ERROR = 1
    WARNING = 2
    INFO = 3
    LOG = 4


# LSP Diagnostic Severity
class DiagnosticSeverity:
    """LSP diagnostic severity levels."""

    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


# LSP Diagnostic Tags
class DiagnosticTag:
    """LSP diagnostic tags."""

    UNNECESSARY = 1  # Unused or unnecessary code
    DEPRECATED = 2  # Deprecated code


# LSP Completion Item Kinds
class CompletionItemKind:
    """LSP completion item kind constants."""

    TEXT = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    FIELD = 5
    VARIABLE = 6
    CLASS = 7
    INTERFACE = 8
    MODULE = 9
    PROPERTY = 10
    UNIT = 11
    VALUE = 12
    ENUM = 13
    KEYWORD = 14
    SNIPPET = 15
    COLOR = 16
    FILE = 17
    REFERENCE = 18


# LSP Symbol Kinds
class SymbolKind:
    """LSP document symbol kind constants."""

    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    ARRAY = 18
