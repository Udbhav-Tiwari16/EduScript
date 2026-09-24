"""
lexer.py
========
Modular, data-driven Lexical Analyzer (Scanner) for customizable programming languages.
Part of Phase 1 (Lexical Analysis) of the Compiler Construction project.

Key Features:
- Preserves original lexemes and tracks exact source positions (line and column).
- Maps custom language keywords to canonical keywords using keyword_mapping.json.
- Dynamically loads operators, delimiters, and token categories from default_tokens.json.
- Gracefully captures and logs lexical errors (unknown characters, unterminated strings/comments).
- Highly readable and modular for Compiler Design students.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class Token:
    """
    Represents an atomic token identified during lexical analysis.

    Attributes:
        type (str): Token classification (e.g., KEYWORD, IDENTIFIER, INTEGER, FLOAT, STRING, etc.).
        lexeme (str): The exact textual representation from the original source code.
        line (int): 1-based source line number where the token begins.
        column (int): 1-based source column number where the token begins.
        canonical (Optional[str]): Canonical/standard keyword meaning (e.g., 'if' for 'agar'), or None.
    """
    type: str
    lexeme: str
    line: int
    column: int
    canonical: Optional[str] = None

    def __repr__(self) -> str:
        canon_str = f", canonical='{self.canonical}'" if self.canonical else ""
        return f"Token(type='{self.type}', lexeme={self.lexeme!r}, line={self.line}, col={self.column}{canon_str})"

    def format_row(self) -> str:
        """Formats the token into a neat table row."""
        canon = f"canonical: {self.canonical}" if self.canonical else "-"
        pos = f"{self.line}:{self.column}"
        return f"{pos:<10} | {self.type:<12} | {self.lexeme:<20} | {canon}"


@dataclass
class LexicalError:
    """
    Represents a lexical error encountered during scanning.

    Attributes:
        message (str): Human-readable error description.
        line (int): 1-based source line number.
        column (int): 1-based source column number.
        lexeme (str): The offending character or string snippet.
    """
    message: str
    line: int
    column: int
    lexeme: str

    def __str__(self) -> str:
        return f"[Line {self.line}, Col {self.column}] Lexical Error: {self.message} -> '{self.lexeme}'"


class Lexer:
    """
    Lexical Analyzer that converts source code into a stream of Tokens.
    """

    def __init__(
        self,
        keyword_mapping: Dict[str, str],
        token_definitions: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the lexer with external configuration and data tables.

        Args:
            keyword_mapping: Mapping of custom keywords to canonical keywords.
            token_definitions: Specifications for operators, delimiters, comments, etc.
            settings: Lexer runtime behavior settings (e.g. whitespace handling).
        """
        self.keyword_mapping = keyword_mapping or {}
        self.token_definitions = token_definitions or {}
        self.settings = settings or {}

        # Configurable lexer behavior
        self.ignore_whitespace = self.settings.get("ignore_whitespace", True)
        self.ignore_comments = self.settings.get("ignore_comments", True)
        self.track_newlines = self.settings.get("track_newlines", False)
        self.case_sensitive = self.settings.get("case_sensitive", True)

        # Build operator table: Sort descending by length so multi-character
        # operators (e.g., '==', '!=', '<=') match before single-character operators ('=', '<')
        raw_operators = self.token_definitions.get("operators", [])
        self.operators = sorted(raw_operators, key=len, reverse=True)

        # Build delimiter table: Sort descending by length for robust matching
        raw_delims = self.token_definitions.get("delimiters", [])
        self.delimiters = sorted(raw_delims, key=len, reverse=True)

        # Comment syntax definitions
        comments_cfg = self.token_definitions.get("comments", {})
        self.single_line_prefixes = comments_cfg.get("single_line", ["//", "#"])
        self.multi_line_start = comments_cfg.get("multi_line_start", "/*")
        self.multi_line_end = comments_cfg.get("multi_line_end", "*/")

        # Scanner state
        self.source = ""
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.errors: List[LexicalError] = []

    def tokenize(self, source_code: str) -> Tuple[List[Token], List[LexicalError]]:
        """
        Tokenizes the entire source code string.

        Args:
            source_code: The raw source program text.

        Returns:
            A tuple of (tokens_list, errors_list).
        """
        self.source = source_code
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []

        while not self._is_at_end():
            self._scan_next_token()

        return self.tokens, self.errors

    # --------------------------------------------------------------------------
    # Helper Scanner Methods
    # --------------------------------------------------------------------------

    def _is_at_end(self) -> bool:
        """Checks if the scanner has reached the end of the source string."""
        return self.pos >= len(self.source)

    def _peek(self, offset: int = 0) -> str:
        """Inspects the character at pos + offset without advancing the cursor."""
        idx = self.pos + offset
        if idx >= len(self.source):
            return ""
        return self.source[idx]

    def _advance(self) -> str:
        """Consumes and returns the current character, incrementing position and column."""
        ch = self.source[self.pos]
        self.pos += 1
        self.column += 1
        return ch

    def _match_prefix(self, prefix: str) -> bool:
        """Checks whether the source starting at the current position begins with prefix."""
        return self.source.startswith(prefix, self.pos)

    # --------------------------------------------------------------------------
    # Main Token Dispatcher
    # --------------------------------------------------------------------------

    def _scan_next_token(self):
        ch = self._peek()

        # 1. Handle Newlines (both Unix '\n' and Windows '\r\n')
        if ch in ('\r', '\n'):
            start_line = self.line
            start_col = self.column
            newline_lexeme = ""
            if ch == '\r' and self._peek(1) == '\n':
                self._advance()
                self._advance()
                newline_lexeme = "\r\n"
            else:
                self._advance()
                newline_lexeme = ch

            self.line += 1
            self.column = 1

            if self.track_newlines:
                self.tokens.append(Token("NEWLINE", repr(newline_lexeme), start_line, start_col))
            return

        # 2. Handle Whitespace (spaces and tabs)
        if ch in (' ', '\t'):
            start_line = self.line
            start_col = self.column
            ws_chars = []
            while not self._is_at_end() and self._peek() in (' ', '\t'):
                ws_chars.append(self._advance())

            if not self.ignore_whitespace:
                self.tokens.append(Token("WHITESPACE", "".join(ws_chars), start_line, start_col))
            return

        # 3. Handle Comments
        # Multi-line comment (e.g. /* ... */)
        if self.multi_line_start and self._match_prefix(self.multi_line_start):
            self._scan_multi_line_comment()
            return

        # Single-line comment (e.g. // or #)
        for prefix in self.single_line_prefixes:
            if self._match_prefix(prefix):
                self._scan_single_line_comment()
                return

        # 4. Handle String Literals (e.g. "hello" or 'world')
        if ch in ('"', "'"):
            self._scan_string(ch)
            return

        # 5. Handle Numeric Literals (Integers and Floats)
        if ch.isdigit():
            self._scan_number()
            return

        # 6. Handle Identifiers and Keywords (begins with letter or underscore)
        if ch.isalpha() or ch == '_':
            self._scan_identifier_or_keyword()
            return

        # 7. Handle Operators (check multi-character before single-character)
        for op in self.operators:
            if self._match_prefix(op):
                start_line = self.line
                start_col = self.column
                for _ in range(len(op)):
                    self._advance()
                self.tokens.append(Token("OPERATOR", op, start_line, start_col))
                return

        # 8. Handle Delimiters (brackets, punctuation, colons, etc.)
        for delim in self.delimiters:
            if self._match_prefix(delim):
                start_line = self.line
                start_col = self.column
                for _ in range(len(delim)):
                    self._advance()
                self.tokens.append(Token("DELIMITER", delim, start_line, start_col))
                return

        # 9. Unrecognized / Unsupported Character (Lexical Error)
        start_line = self.line
        start_col = self.column
        bad_char = self._advance()
        error = LexicalError(
            message=f"Unsupported character '{bad_char}'",
            line=start_line,
            column=start_col,
            lexeme=bad_char
        )
        self.errors.append(error)
        self.tokens.append(Token("UNKNOWN", bad_char, start_line, start_col))

    # --------------------------------------------------------------------------
    # Specialized Token Scanners
    # --------------------------------------------------------------------------

    def _scan_single_line_comment(self):
        """Scans single-line comment up to newline or EOF."""
        start_line = self.line
        start_col = self.column
        chars = []

        while not self._is_at_end() and self._peek() not in ('\r', '\n'):
            chars.append(self._advance())

        lexeme = "".join(chars)
        if not self.ignore_comments:
            self.tokens.append(Token("COMMENT", lexeme, start_line, start_col))

    def _scan_multi_line_comment(self):
        """Scans block comment until closing marker or EOF."""
        start_line = self.line
        start_col = self.column
        chars = []

        # Consume opening marker
        for _ in range(len(self.multi_line_start)):
            chars.append(self._advance())

        closed = False
        while not self._is_at_end():
            if self._match_prefix(self.multi_line_end):
                for _ in range(len(self.multi_line_end)):
                    chars.append(self._advance())
                closed = True
                break

            ch = self._peek()
            if ch == '\n':
                chars.append(self._advance())
                self.line += 1
                self.column = 1
            elif ch == '\r':
                chars.append(self._advance())
                if self._peek() == '\n':
                    chars.append(self._advance())
                self.line += 1
                self.column = 1
            else:
                chars.append(self._advance())

        lexeme = "".join(chars)
        if not closed:
            self.errors.append(LexicalError(
                message="Unterminated multi-line comment",
                line=start_line,
                column=start_col,
                lexeme=lexeme
            ))
            self.tokens.append(Token("UNKNOWN", lexeme, start_line, start_col))
        elif not self.ignore_comments:
            self.tokens.append(Token("COMMENT", lexeme, start_line, start_col))

    def _scan_string(self, quote_char: str):
        """Scans quoted string literals, handling escape characters."""
        start_line = self.line
        start_col = self.column
        chars = [self._advance()]  # Include opening quote

        terminated = False
        while not self._is_at_end():
            ch = self._peek()

            # Disallow unescaped raw newlines inside standard strings
            if ch in ('\r', '\n'):
                break

            # Handle escape sequences (e.g. \", \\, \n)
            if ch == '\\':
                chars.append(self._advance())
                if not self._is_at_end():
                    chars.append(self._advance())
                continue

            # Found matching closing quote
            if ch == quote_char:
                chars.append(self._advance())
                terminated = True
                break

            chars.append(self._advance())

        lexeme = "".join(chars)
        if not terminated:
            self.errors.append(LexicalError(
                message="Unterminated string literal",
                line=start_line,
                column=start_col,
                lexeme=lexeme
            ))
            self.tokens.append(Token("UNKNOWN", lexeme, start_line, start_col))
        else:
            self.tokens.append(Token("STRING", lexeme, start_line, start_col))

    def _scan_number(self):
        """Scans integer or floating point numeric literals."""
        start_line = self.line
        start_col = self.column
        chars = []

        # Scan integer digits
        while not self._is_at_end() and self._peek().isdigit():
            chars.append(self._advance())

        is_float = False
        # Lookahead for decimal point followed immediately by digits
        if self._peek() == '.' and self._peek(1).isdigit():
            is_float = True
            chars.append(self._advance())  # Consume '.'
            while not self._is_at_end() and self._peek().isdigit():
                chars.append(self._advance())

        # Check for malformed identifiers beginning with numbers (e.g. 10abc)
        if not self._is_at_end() and (self._peek().isalpha() or self._peek() == '_'):
            while not self._is_at_end() and (self._peek().isalnum() or self._peek() == '_'):
                chars.append(self._advance())
            bad_lexeme = "".join(chars)
            self.errors.append(LexicalError(
                message=f"Malformed numeric literal '{bad_lexeme}'",
                line=start_line,
                column=start_col,
                lexeme=bad_lexeme
            ))
            self.tokens.append(Token("UNKNOWN", bad_lexeme, start_line, start_col))
            return

        lexeme = "".join(chars)
        token_type = "FLOAT" if is_float else "INTEGER"
        self.tokens.append(Token(token_type, lexeme, start_line, start_col))

    def _scan_identifier_or_keyword(self):
        """Scans identifier, then checks against custom keyword mapping."""
        start_line = self.line
        start_col = self.column
        chars = []

        while not self._is_at_end() and (self._peek().isalnum() or self._peek() == '_'):
            chars.append(self._advance())

        lexeme = "".join(chars)
        lookup_key = lexeme if self.case_sensitive else lexeme.lower()

        # Check if the word is in the keyword mapping dictionary
        if lookup_key in self.keyword_mapping:
            canonical_meaning = self.keyword_mapping[lookup_key]
            self.tokens.append(Token(
                type="KEYWORD",
                lexeme=lexeme,
                line=start_line,
                column=start_col,
                canonical=canonical_meaning
            ))
        else:
            self.tokens.append(Token(
                type="IDENTIFIER",
                lexeme=lexeme,
                line=start_line,
                column=start_col
            ))
