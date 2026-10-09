"""
parser.py
=========
Recursive Descent Parser for EduScript compiler.
Converts the stream of Tokens from lexer.py into an Abstract Syntax Tree (AST).

Key Features:
- Consumes standard EduScript Token objects seamlessly.
- Handles custom keywords via normalized canonical tags (agar -> if, jabtak -> while, purnaank -> int, etc.).
- Complete grammar support:
  * Variable declarations with optional initialization (int, float, string, bool)
  * Assignment and compound assignments (=, +=, -=, *=, /=)
  * Conditional branching (if / else)
  * Loops (while, for)
  * Built-in print (print / dikhao)
  * Return statements (return / wapas)
  * Block scopes ({ ... })
  * Full operator precedence for arithmetic, relational, and logical expressions
- Rich syntax error recovery and diagnostic messages with exact source locations.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

from lexer import Token
from ast_nodes import (
    ASTNode, Program, Stmt, Expr,
    VarDecl, Block, IfStmt, WhileStmt, ForStmt,
    PrintStmt, ReturnStmt, ExprStmt, FuncDecl,
    LiteralExpr, IdentifierExpr, BinaryExpr, UnaryExpr,
    AssignExpr, CallExpr, GroupExpr
)


@dataclass
class ParseError:
    """Represents a syntax error encountered during parsing."""
    message: str
    line: int
    column: int
    token: Optional[Token] = None

    def __str__(self) -> str:
        tok_str = f" at '{self.token.lexeme}'" if self.token else ""
        return f"[Line {self.line}, Col {self.column}] Syntax Error: {self.message}{tok_str}"


class Parser:
    """
    Recursive Descent Parser for the EduScript language.
    """

    TYPE_KEYWORDS = {"int", "float", "string", "bool"}

    def __init__(self, tokens: List[Token]):
        # Filter out comments and whitespace if present in token stream
        self.tokens: List[Token] = [
            t for t in tokens if t.type not in ("COMMENT", "WHITESPACE", "NEWLINE")
        ]
        self.current = 0
        self.errors: List[ParseError] = []

    # -------------------------------------------------------------------------
    # Public Entry Point
    # -------------------------------------------------------------------------

    def parse(self) -> Tuple[Optional[Program], List[ParseError]]:
        """
        Parses the entire token stream into a Program AST node.

        Returns:
            A tuple of (Program AST or None, list of ParseErrors).
        """
        self.current = 0
        self.errors = []
        statements: List[Stmt] = []

        first_line = self.tokens[0].line if self.tokens else 1
        first_col = self.tokens[0].column if self.tokens else 1

        while not self._is_at_end():
            try:
                stmt = self._declaration()
                if stmt is not None:
                    statements.append(stmt)
            except ParseException:
                self._synchronize()

        program = Program(statements=statements, line=first_line, column=first_col)
        return program, self.errors

    # -------------------------------------------------------------------------
    # Grammar Rules: Declarations & Statements
    # -------------------------------------------------------------------------

    def _declaration(self) -> Optional[Stmt]:
        """
        Declaration -> VarDecl | FuncDecl | Statement
        """
        if self._check_type_keyword():
            # Check if this is a function definition or variable declaration
            if self._peek_ahead(1) and self._peek_ahead(1).type == "IDENTIFIER" and \
               self._peek_ahead(2) and self._peek_ahead(2).is_delimiter("("):
                return self._function_declaration()
            return self._var_declaration()

        if self._check_keyword("def"):
            return self._function_declaration()

        return self._statement()

    def _var_declaration(self) -> VarDecl:
        """
        VarDecl -> Type IDENTIFIER ('=' Expression)? ';'
        """
        type_tok = self._advance()
        type_name = type_tok.canonical if type_tok.canonical else type_tok.lexeme

        id_tok = self._consume("IDENTIFIER", "Expected variable identifier after type")
        var_name = id_tok.lexeme

        initializer: Optional[Expr] = None
        if self._match_operator("="):
            initializer = self._expression()

        self._consume_delimiter(";", "Expected ';' after variable declaration")
        return VarDecl(
            var_type=type_name,
            name=var_name,
            initializer=initializer,
            line=type_tok.line,
            column=type_tok.column
        )

    def _function_declaration(self) -> FuncDecl:
        """
        FuncDecl -> ('def' | Type) IDENTIFIER '(' Parameters? ')' Block
        """
        line, col = self._peek().line, self._peek().column
        return_type = "void"
        if self._match_keyword("def"):
            return_type = "void"
        elif self._check_type_keyword():
            t_tok = self._advance()
            return_type = t_tok.canonical if t_tok.canonical else t_tok.lexeme

        id_tok = self._consume("IDENTIFIER", "Expected function name")
        name = id_tok.lexeme

        self._consume_delimiter("(", "Expected '(' after function name")
        params: List[Tuple[str, str]] = []
        if not self._check_delimiter(")"):
            while True:
                if not self._check_type_keyword():
                    self._error("Expected parameter type")
                p_type_tok = self._advance()
                p_type = p_type_tok.canonical if p_type_tok.canonical else p_type_tok.lexeme
                p_id = self._consume("IDENTIFIER", "Expected parameter name").lexeme
                params.append((p_type, p_id))
                if not self._match_delimiter(","):
                    break

        self._consume_delimiter(")", "Expected ')' after parameters")
        body = self._block_statement()
        return FuncDecl(
            return_type=return_type,
            name=name,
            params=params,
            body=body,
            line=line,
            column=col
        )

    def _statement(self) -> Stmt:
        """
        Statement -> Block | IfStmt | WhileStmt | ForStmt | PrintStmt | ReturnStmt | ExprStmt
        """
        if self._check_delimiter("{"):
            return self._block_statement()
        if self._match_keyword("if"):
            return self._if_statement()
        if self._match_keyword("while"):
            return self._while_statement()
        if self._match_keyword("for"):
            return self._for_statement()
        if self._match_keyword("print"):
            return self._print_statement()
        if self._match_keyword("return"):
            return self._return_statement()

        return self._expression_statement()

    def _block_statement(self) -> Block:
        """
        Block -> '{' Declaration* '}'
        """
        open_tok = self._consume_delimiter("{", "Expected '{' to start block")
        statements: List[Stmt] = []

        while not self._check_delimiter("}") and not self._is_at_end():
            stmt = self._declaration()
            if stmt is not None:
                statements.append(stmt)

        self._consume_delimiter("}", "Expected '}' after block")
        return Block(statements=statements, line=open_tok.line, column=open_tok.column)

    def _if_statement(self) -> IfStmt:
        """
        IfStmt -> 'if' '(' Expression ')' Statement ('else' Statement)?
        """
        if_tok = self._previous()
        self._consume_delimiter("(", "Expected '(' after 'if'")
        condition = self._expression()
        self._consume_delimiter(")", "Expected ')' after if condition")

        then_branch = self._statement()
        else_branch: Optional[Stmt] = None
        if self._match_keyword("else"):
            else_branch = self._statement()

        return IfStmt(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=if_tok.line,
            column=if_tok.column
        )

    def _while_statement(self) -> WhileStmt:
        """
        WhileStmt -> 'while' '(' Expression ')' Statement
        """
        while_tok = self._previous()
        self._consume_delimiter("(", "Expected '(' after 'while'")
        condition = self._expression()
        self._consume_delimiter(")", "Expected ')' after while condition")
        body = self._statement()

        return WhileStmt(
            condition=condition,
            body=body,
            line=while_tok.line,
            column=while_tok.column
        )

    def _for_statement(self) -> ForStmt:
        """
        ForStmt -> 'for' '(' (VarDecl | ExprStmt | ';') Expression? ';' Expression? ')' Statement
        """
        for_tok = self._previous()
        self._consume_delimiter("(", "Expected '(' after 'for'")

        # 1. Initializer
        init: Optional[Stmt] = None
        if self._match_delimiter(";"):
            init = None
        elif self._check_type_keyword():
            init = self._var_declaration()
        else:
            init = self._expression_statement()

        # 2. Condition
        condition: Optional[Expr] = None
        if not self._check_delimiter(";"):
            condition = self._expression()
        self._consume_delimiter(";", "Expected ';' after for loop condition")

        # 3. Update expression
        update: Optional[Expr] = None
        if not self._check_delimiter(")"):
            update = self._expression()
        self._consume_delimiter(")", "Expected ')' after for clauses")

        body = self._statement()
        return ForStmt(
            init=init,
            condition=condition,
            update=update,
            body=body,
            line=for_tok.line,
            column=for_tok.column
        )

    def _print_statement(self) -> PrintStmt:
        """
        PrintStmt -> 'print' '(' (Expression (',' Expression)*)? ')' ';'
        """
        print_tok = self._previous()
        self._consume_delimiter("(", "Expected '(' after 'print'")
        expressions: List[Expr] = []

        if not self._check_delimiter(")"):
            while True:
                expressions.append(self._expression())
                if not self._match_delimiter(","):
                    break

        self._consume_delimiter(")", "Expected ')' after print arguments")
        self._consume_delimiter(";", "Expected ';' after print statement")
        return PrintStmt(
            expressions=expressions,
            line=print_tok.line,
            column=print_tok.column
        )

    def _return_statement(self) -> ReturnStmt:
        """
        ReturnStmt -> 'return' Expression? ';'
        """
        ret_tok = self._previous()
        value: Optional[Expr] = None
        if not self._check_delimiter(";"):
            value = self._expression()

        self._consume_delimiter(";", "Expected ';' after return statement")
        return ReturnStmt(value=value, line=ret_tok.line, column=ret_tok.column)

    def _expression_statement(self) -> ExprStmt:
        """
        ExprStmt -> Expression ';'
        """
        expr = self._expression()
        self._consume_delimiter(";", "Expected ';' after expression")
        return ExprStmt(expression=expr, line=expr.line, column=expr.column)

    # -------------------------------------------------------------------------
    # Grammar Rules: Expressions (Precedence Climbing)
    # -------------------------------------------------------------------------

    def _expression(self) -> Expr:
        """Expression -> Assignment"""
        return self._assignment()

    def _assignment(self) -> Expr:
        """
        Assignment -> IDENTIFIER ('=' | '+=' | '-=' | '*=' | '/=') Assignment | LogicalOr
        """
        expr = self._logical_or()

        # Check for assignment operators
        if self._check_any_operator(["=", "+=", "-=", "*=", "/="]):
            op_tok = self._advance()
            operator = op_tok.lexeme
            value = self._assignment()

            if isinstance(expr, IdentifierExpr):
                return AssignExpr(
                    target=expr.name,
                    operator=operator,
                    value=value,
                    line=expr.line,
                    column=expr.column
                )
            self._error(f"Invalid assignment target at line {expr.line}, col {expr.column}")

        return expr

    def _logical_or(self) -> Expr:
        """LogicalOr -> LogicalAnd ('||' LogicalAnd)*"""
        expr = self._logical_and()
        while self._match_operator("||"):
            op = self._previous().lexeme
            right = self._logical_and()
            expr = BinaryExpr(left=expr, operator=op, right=right, line=expr.line, column=expr.column)
        return expr

    def _logical_and(self) -> Expr:
        """LogicalAnd -> Equality ('&&' Equality)*"""
        expr = self._equality()
        while self._match_operator("&&"):
            op = self._previous().lexeme
            right = self._equality()
            expr = BinaryExpr(left=expr, operator=op, right=right, line=expr.line, column=expr.column)
        return expr

    def _equality(self) -> Expr:
        """Equality -> Relational (('==' | '!=') Relational)*"""
        expr = self._relational()
        while self._check_any_operator(["==", "!="]):
            op = self._advance().lexeme
            right = self._relational()
            expr = BinaryExpr(left=expr, operator=op, right=right, line=expr.line, column=expr.column)
        return expr

    def _relational(self) -> Expr:
        """Relational -> Additive (('<' | '<=' | '>' | '>=') Additive)*"""
        expr = self._additive()
        while self._check_any_operator(["<", "<=", ">", ">="]):
            op = self._advance().lexeme
            right = self._additive()
            expr = BinaryExpr(left=expr, operator=op, right=right, line=expr.line, column=expr.column)
        return expr

    def _additive(self) -> Expr:
        """Additive -> Multiplicative (('+' | '-') Multiplicative)*"""
        expr = self._multiplicative()
        while self._check_any_operator(["+", "-"]):
            op = self._advance().lexeme
            right = self._multiplicative()
            expr = BinaryExpr(left=expr, operator=op, right=right, line=expr.line, column=expr.column)
        return expr

    def _multiplicative(self) -> Expr:
        """Multiplicative -> Unary (('*' | '/' | '%') Unary)*"""
        expr = self._unary()
        while self._check_any_operator(["*", "/", "%"]):
            op = self._advance().lexeme
            right = self._unary()
            expr = BinaryExpr(left=expr, operator=op, right=right, line=expr.line, column=expr.column)
        return expr

    def _unary(self) -> Expr:
        """Unary -> ('!' | '-' | '+') Unary | Primary"""
        if self._check_any_operator(["!", "-", "+"]):
            op_tok = self._advance()
            operand = self._unary()
            return UnaryExpr(operator=op_tok.lexeme, operand=operand, line=op_tok.line, column=op_tok.column)
        return self._primary()

    def _primary(self) -> Expr:
        """
        Primary -> INTEGER | FLOAT | STRING | 'true' | 'false' | IDENTIFIER ('(' (Expr (',' Expr)*)? ')')? | '(' Expression ')'
        """
        tok = self._peek()

        if tok.type == "INTEGER":
            self._advance()
            return LiteralExpr(value=int(tok.lexeme), type_name="int", line=tok.line, column=tok.column)

        if tok.type == "FLOAT":
            self._advance()
            return LiteralExpr(value=float(tok.lexeme), type_name="float", line=tok.line, column=tok.column)

        if tok.type == "STRING":
            self._advance()
            # Strip quotes and handle basic escape characters
            raw = tok.lexeme
            if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
                inner = raw[1:-1]
                # Unescape common escapes
                inner = inner.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
            else:
                inner = raw
            return LiteralExpr(value=inner, type_name="string", line=tok.line, column=tok.column)

        if tok.type == "KEYWORD":
            if tok.canonical == "true":
                self._advance()
                return LiteralExpr(value=True, type_name="bool", line=tok.line, column=tok.column)
            elif tok.canonical == "false":
                self._advance()
                return LiteralExpr(value=False, type_name="bool", line=tok.line, column=tok.column)

        if tok.type == "IDENTIFIER":
            self._advance()
            # Check for function call
            if self._match_delimiter("("):
                args: List[Expr] = []
                if not self._check_delimiter(")"):
                    while True:
                        args.append(self._expression())
                        if not self._match_delimiter(","):
                            break
                self._consume_delimiter(")", "Expected ')' after function arguments")
                return CallExpr(callee=tok.lexeme, args=args, line=tok.line, column=tok.column)
            return IdentifierExpr(name=tok.lexeme, line=tok.line, column=tok.column)

        if self._match_delimiter("("):
            open_tok = self._previous()
            expr = self._expression()
            self._consume_delimiter(")", "Expected ')' after expression")
            return GroupExpr(expression=expr, line=open_tok.line, column=open_tok.column)

        # If nothing matches, raise parse error
        raise self._error(f"Unexpected token '{tok.lexeme}' (type: {tok.type})")

    # -------------------------------------------------------------------------
    # Helper Inspection & Consumption Methods
    # -------------------------------------------------------------------------

    def _is_at_end(self) -> bool:
        return self.current >= len(self.tokens)

    def _peek(self) -> Token:
        if self._is_at_end():
            # Synthesize EOF token
            last_line = self.tokens[-1].line if self.tokens else 1
            last_col = self.tokens[-1].column if self.tokens else 1
            return Token("EOF", "<EOF>", last_line, last_col)
        return self.tokens[self.current]

    def _peek_ahead(self, offset: int) -> Optional[Token]:
        idx = self.current + offset
        if idx >= len(self.tokens):
            return None
        return self.tokens[idx]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _check_keyword(self, canonical_name: str) -> bool:
        if self._is_at_end():
            return False
        tok = self._peek()
        return tok.type == "KEYWORD" and tok.canonical == canonical_name

    def _match_keyword(self, canonical_name: str) -> bool:
        if self._check_keyword(canonical_name):
            self._advance()
            return True
        return False

    def _check_type_keyword(self) -> bool:
        if self._is_at_end():
            return False
        tok = self._peek()
        return tok.type == "KEYWORD" and tok.canonical in self.TYPE_KEYWORDS

    def _check_operator(self, op: str) -> bool:
        if self._is_at_end():
            return False
        tok = self._peek()
        return tok.type == "OPERATOR" and tok.lexeme == op

    def _check_any_operator(self, ops: List[str]) -> bool:
        if self._is_at_end():
            return False
        tok = self._peek()
        return tok.type == "OPERATOR" and tok.lexeme in ops

    def _match_operator(self, op: str) -> bool:
        if self._check_operator(op):
            self._advance()
            return True
        return False

    def _check_delimiter(self, delim: str) -> bool:
        if self._is_at_end():
            return False
        tok = self._peek()
        return tok.type == "DELIMITER" and tok.lexeme == delim

    def _match_delimiter(self, delim: str) -> bool:
        if self._check_delimiter(delim):
            self._advance()
            return True
        return False

    def _consume(self, token_type: str, message: str) -> Token:
        if not self._is_at_end() and self._peek().type == token_type:
            return self._advance()
        raise self._error(message)

    def _consume_delimiter(self, delim: str, message: str) -> Token:
        if not self._is_at_end() and self._peek().type == "DELIMITER" and self._peek().lexeme == delim:
            return self._advance()
        raise self._error(message)

    def _error(self, message: str) -> "ParseException":
        tok = self._peek()
        err = ParseError(message=message, line=tok.line, column=tok.column, token=tok)
        self.errors.append(err)
        return ParseException(err)

    def _synchronize(self):
        """Discards tokens until a safe statement boundary is found."""
        self._advance()
        while not self._is_at_end():
            if self._previous().type == "DELIMITER" and self._previous().lexeme == ";":
                return
            tok = self._peek()
            if tok.type == "KEYWORD" and tok.canonical in (
                "if", "while", "for", "int", "float", "string", "bool", "print", "return", "def"
            ):
                return
            if tok.type == "DELIMITER" and tok.lexeme == "}":
                return
            self._advance()


class ParseException(Exception):
    """Internal exception to unwind parsing stack during error recovery."""
    def __init__(self, error: ParseError):
        super().__init__(error.message)
        self.error = error
