"""
8085 Assembly Language Server Protocol (LSP) implementation.

Main server that coordinates all LSP features:
- Diagnostics (errors and warnings)
- Code completion
- Hover documentation
- Go to definition
- Document symbols
- Signature help
"""

import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .diagnostics import DiagnosticsCollector
from .features import (
    CompletionProvider,
    DefinitionProvider,
    HoverProvider,
    SignatureHelpProvider,
    SymbolsProvider,
)
from .protocol import (
    DiagnosticSeverity,
    ErrorCodes,
    LSPProtocol,
    MessageType,
)


class LSPServer:
    """
    Main LSP server for 8085 Assembly.

    Manages:
    - Document lifecycle (open, change, save, close)
    - Asynchronous diagnostics collection
    - Feature providers (completion, hover, etc.)
    - LSP protocol communication
    """

    def __init__(self):
        """Initialize the LSP server."""
        # Protocol handler
        self.protocol = LSPProtocol()

        # Document storage
        self.documents: Dict[str, str] = {}

        # Feature providers
        self.diagnostics = DiagnosticsCollector()
        self.completion = CompletionProvider()
        self.hover = HoverProvider()
        self.definition = DefinitionProvider()
        self.symbols = SymbolsProvider()
        self.signature_help = SignatureHelpProvider()

        # Async diagnostics
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lsp-diag")
        self._diagnostic_tokens: Dict[str, int] = {}
        self._diagnostic_lock = threading.Lock()

        # Label cache for features
        self._label_cache: Dict[str, Dict[str, int]] = {}
        self._cache_lock = threading.Lock()

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging to send messages to LSP client."""
        log_level_str = os.environ.get("ASM8085_LSP_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, log_level_str, logging.INFO)

        logging.basicConfig(
            level=level,
            format="[%(levelname)s] %(message)s",
            handlers=[LSPLogHandler(self)],
        )
        logging.info("8085 Assembly LSP server starting")

    def run(self):
        """Main server loop - read and handle messages until shutdown."""
        logging.info("LSP server ready")

        try:
            while True:
                message = self.protocol.read_message()
                if message is None:
                    # End of stream or read error
                    break

                response = self._handle_message(message)
                if response:
                    self.protocol.write_message(response)

        except KeyboardInterrupt:
            logging.info("Server interrupted")
        except Exception as e:
            logging.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            self._shutdown()

    def _shutdown(self):
        """Clean shutdown of server resources."""
        logging.info("Shutting down LSP server")
        self.executor.shutdown(wait=False)

    def _handle_message(self, message: Dict[str, Any]) -> Optional[Dict]:
        """
        Route incoming message to appropriate handler.

        Args:
            message: JSON-RPC message

        Returns:
            Response message or None for notifications
        """
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")

        # Lifecycle methods
        if method == "initialize":
            return self._handle_initialize(msg_id, params)
        elif method == "initialized":
            return None  # Notification, no response
        elif method == "shutdown":
            return {"id": msg_id, "result": None}
        elif method == "exit":
            sys.exit(0)

        # Document synchronization
        elif method == "textDocument/didOpen":
            self._handle_did_open(params)
            return None
        elif method == "textDocument/didChange":
            self._handle_did_change(params)
            return None
        elif method == "textDocument/didSave":
            self._handle_did_save(params)
            return None
        elif method == "textDocument/didClose":
            self._handle_did_close(params)
            return None

        # Language features
        elif method == "textDocument/completion":
            return self._handle_completion(msg_id, params)
        elif method == "textDocument/hover":
            return self._handle_hover(msg_id, params)
        elif method == "textDocument/definition":
            return self._handle_definition(msg_id, params)
        elif method == "textDocument/documentSymbol":
            return self._handle_document_symbol(msg_id, params)
        elif method == "textDocument/signatureHelp":
            return self._handle_signature_help(msg_id, params)

        # Ignore cancelation and other notifications
        elif method in ("$/cancelRequest", "$/setTrace"):
            return None

        else:
            logging.warning(f"Unhandled method: {method}")
            return None

    # -------------------------------------------------------------------------
    # Lifecycle handlers
    # -------------------------------------------------------------------------

    def _handle_initialize(self, msg_id: int, params: Dict) -> Dict:
        """Handle initialize request."""
        logging.info("Handling initialize request")

        return {
            "id": msg_id,
            "result": {
                "capabilities": {
                    "textDocumentSync": 1,  # Full sync
                    "completionProvider": {
                        "triggerCharacters": [" ", ",", "\t"],
                    },
                    "hoverProvider": True,
                    "definitionProvider": True,
                    "documentSymbolProvider": True,
                    "signatureHelpProvider": {
                        "triggerCharacters": [" ", ","],
                    },
                },
                "serverInfo": {
                    "name": "asm8085-lsp",
                    "version": "0.2.1",
                },
            },
        }

    # -------------------------------------------------------------------------
    # Document synchronization handlers
    # -------------------------------------------------------------------------

    def _handle_did_open(self, params: Dict) -> None:
        """Handle document open notification."""
        doc = params["textDocument"]
        uri = doc["uri"]
        text = doc["text"]

        self.documents[uri] = text
        logging.info(f"Document opened: {uri}")

        # Trigger diagnostics
        self._schedule_diagnostics(uri, text)

    def _handle_did_change(self, params: Dict) -> None:
        """Handle document change notification."""
        uri = params["textDocument"]["uri"]
        text = params["contentChanges"][0]["text"]

        self.documents[uri] = text

        # Trigger diagnostics
        self._schedule_diagnostics(uri, text)

    def _handle_did_save(self, params: Dict) -> None:
        """Handle document save notification."""
        uri = params["textDocument"]["uri"]

        # If server sends full text on save, update it
        if "text" in params:
            text = params["text"]
            self.documents[uri] = text
            self._schedule_diagnostics(uri, text)

    def _handle_did_close(self, params: Dict) -> None:
        """Handle document close notification."""
        uri = params["textDocument"]["uri"]

        # Clean up all cached data for this document
        self.documents.pop(uri, None)
        self.diagnostics.clear_cache(uri)

        with self._cache_lock:
            self._label_cache.pop(uri, None)

        logging.info(f"Document closed: {uri}")

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    def _schedule_diagnostics(self, uri: str, text: str) -> None:
        """
        Schedule asynchronous diagnostics collection.

        Uses token-based cancellation to avoid stale diagnostics.
        """
        with self._diagnostic_lock:
            token = self._diagnostic_tokens.get(uri, 0) + 1
            self._diagnostic_tokens[uri] = token

        # Run in background
        self.executor.submit(self._collect_and_publish_diagnostics, uri, text, token)

    def _collect_and_publish_diagnostics(self, uri: str, text: str, token: int) -> None:
        """
        Collect diagnostics and publish them if token is still current.

        Args:
            uri: Document URI
            text: Document text
            token: Cancellation token
        """
        # Check if this request is still current
        if not self._is_token_current(uri, token):
            return

        # Collect diagnostics from assembler
        diagnostics_list, label_map = self.diagnostics.collect_from_assembly(uri, text)

        # Check again after potentially slow operation
        if not self._is_token_current(uri, token):
            return

        # Update caches
        self.diagnostics.update_cache(uri, diagnostics_list)

        if label_map:
            with self._cache_lock:
                self._label_cache[uri] = label_map

            # Update feature providers with new labels
            label_names = list(label_map.keys())
            self.completion.update_labels(uri, label_names)
            self.hover.update_labels(uri, label_map)
            self.definition.update_labels(uri, label_map)

        # Update symbols
        lines = text.splitlines()
        self.symbols.update_labels(uri, lines)

        # Publish diagnostics to client
        lsp_diagnostics = self.diagnostics.to_lsp_format(diagnostics_list)
        self.protocol.write_notification(
            "textDocument/publishDiagnostics",
            {"uri": uri, "diagnostics": lsp_diagnostics},
        )

        logging.debug(f"Published {len(lsp_diagnostics)} diagnostics for {uri}")

    def _is_token_current(self, uri: str, token: int) -> bool:
        """Check if diagnostic token is still current (not cancelled)."""
        with self._diagnostic_lock:
            return self._diagnostic_tokens.get(uri) == token

    # -------------------------------------------------------------------------
    # Language feature handlers
    # -------------------------------------------------------------------------

    def _handle_completion(self, msg_id: int, params: Dict) -> Dict:
        """Handle completion request."""
        uri = params["textDocument"]["uri"]
        position = params["position"]
        line_num = position["line"]
        character = position["character"]

        # Get document text
        text = self.documents.get(uri, "")
        lines = text.splitlines()

        if line_num >= len(lines):
            return {"id": msg_id, "result": {"isIncomplete": False, "items": []}}

        line = lines[line_num]

        # Get completions from provider
        items = self.completion.provide_completion(uri, line, character)

        return {"id": msg_id, "result": {"isIncomplete": False, "items": items}}

    def _handle_hover(self, msg_id: int, params: Dict) -> Dict:
        """Handle hover request."""
        uri = params["textDocument"]["uri"]
        position = params["position"]
        line_num = position["line"]
        character = position["character"]

        # Get document text
        text = self.documents.get(uri, "")
        lines = text.splitlines()

        if line_num >= len(lines):
            return {"id": msg_id, "result": None}

        line = lines[line_num]

        # Extract word at position
        word = self._extract_word_at_position(line, character)
        if not word:
            return {"id": msg_id, "result": None}

        # Get hover from provider
        hover = self.hover.provide_hover(uri, word)

        return {"id": msg_id, "result": hover}

    def _handle_definition(self, msg_id: int, params: Dict) -> Dict:
        """Handle go-to-definition request."""
        uri = params["textDocument"]["uri"]
        position = params["position"]
        line_num = position["line"]
        character = position["character"]

        # Get document text
        text = self.documents.get(uri, "")
        lines = text.splitlines()

        if line_num >= len(lines):
            return {"id": msg_id, "result": None}

        line = lines[line_num]

        # Extract word at position
        word = self._extract_word_at_position(line, character)
        if not word:
            return {"id": msg_id, "result": None}

        # Get definition from provider
        definition = self.definition.provide_definition(uri, word)

        return {"id": msg_id, "result": definition}

    def _handle_document_symbol(self, msg_id: int, params: Dict) -> Dict:
        """Handle document symbols request."""
        uri = params["textDocument"]["uri"]

        # Get symbols from provider
        symbols = self.symbols.provide_symbols(uri)

        return {"id": msg_id, "result": symbols}

    def _handle_signature_help(self, msg_id: int, params: Dict) -> Dict:
        """Handle signature help request."""
        uri = params["textDocument"]["uri"]
        position = params["position"]
        line_num = position["line"]
        character = position["character"]

        # Get document text
        text = self.documents.get(uri, "")
        lines = text.splitlines()

        if line_num >= len(lines):
            return {"id": msg_id, "result": None}

        line = lines[line_num]

        # Get signature help from provider
        sig_help = self.signature_help.provide_signature_help(line, character)

        return {"id": msg_id, "result": sig_help}

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    def _extract_word_at_position(self, line: str, character: int) -> str:
        """Extract word at cursor position."""
        if character > len(line):
            character = len(line)

        # Find word boundaries
        start = character
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1

        end = character
        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1

        return line[start:end]

    def send_log_message(self, message: str, level: int = MessageType.INFO) -> None:
        """Send log message to client."""
        self.protocol.write_notification(
            "window/logMessage", {"type": level, "message": message}
        )


class LSPLogHandler(logging.Handler):
    """Custom logging handler that sends logs to LSP client."""

    def __init__(self, server: LSPServer):
        super().__init__()
        self.server = server

    def emit(self, record):
        """Emit log record as LSP window/logMessage notification."""
        try:
            message = self.format(record)

            # Map Python log levels to LSP message types
            level_map = {
                logging.CRITICAL: MessageType.ERROR,
                logging.ERROR: MessageType.ERROR,
                logging.WARNING: MessageType.WARNING,
                logging.INFO: MessageType.INFO,
                logging.DEBUG: MessageType.LOG,
            }
            lsp_level = level_map.get(record.levelno, MessageType.LOG)

            self.server.send_log_message(message, lsp_level)
        except Exception:
            # Avoid logging errors causing loops
            pass


def main():
    """Entry point for the LSP server."""

    server = LSPServer()
    server.run()


if __name__ == "__main__":
    main()
