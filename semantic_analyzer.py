"""
semantic_analyzer.py
====================
Semantic Analysis stage for EduScript compiler.
Performs scoped symbol table management, type checking, declaration validation,
undeclared variable detection, and diagnostic reporting.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

from ast_nodes import (
    ASTVisitor, ASTNode, Program, Stmt, Expr,
    VarDecl, Block, IfStmt, WhileStmt, ForStmt,
    PrintStmt, ReturnStmt, ExprStmt, FuncDecl,
    LiteralExpr, IdentifierExpr, BinaryExpr, UnaryExpr,
    AssignExpr, CallExpr, GroupExpr
)
from symbol_table import SymbolTable, Symbol


@dataclass
class SemanticError:
    """Represents a semantic violation in the source code."""
    message: str
    line: int
    column: int
    error_type: str = "SemanticError"

    def __str__(self) -> str:
        return f"[Line {self.line}, Col {self.column}] {self.error_type}: {self.message}"


@dataclass
class SemanticWarning:
    """Represents a non-fatal semantic warning (e.g. uninitialized variable read)."""
    message: str
    line: int
    column: int
    warning_type: str = "SemanticWarning"

    def __str__(self) -> str:
        return f"[Line {self.line}, Col {self.column}] {self.warning_type}: {self.message}"


class SemanticAnalyzer(ASTVisitor):
    """
    Traverses the AST to validate types, scopes, and symbol declarations.
    """

    def __init__(self, symbol_table: Optional[SymbolTable] = None):
        self.symbol_table = symbol_table if symbol_table is not None else SymbolTable()
        self.errors: List[SemanticError] = []
        self.warnings: List[SemanticWarning] = []
        self.current_function_return_type: Optional[str] = None

    def analyze(self, program: Program) -> Tuple[SymbolTable, List[SemanticError], List[SemanticWarning]]:
        """
        Runs semantic analysis on the entire AST program.

        Returns:
            A tuple of (populated SymbolTable, list of SemanticErrors, list of SemanticWarnings).
        """
        self.errors = []
        self.warnings = []
        program.accept(self)
        return self.symbol_table, self.errors, self.warnings

    # -------------------------------------------------------------------------
    # Helper Validation & Type System Methods
    # -------------------------------------------------------------------------

    def _is_type_compatible(self, target_type: str, expr_type: str) -> bool:
        """Checks if expr_type can be assigned to target_type."""
        if target_type == expr_type:
            return True
        # Allow implicit widening from int to float
        if target_type == "float" and expr_type == "int":
            return True
        # Any type can be converted or printed
        if target_type == "any" or expr_type == "any":
            return True
        return False

    def _error(self, message: str, node: ASTNode, error_type: str = "SemanticError"):
        self.errors.append(SemanticError(message=message, line=node.line, column=node.column, error_type=error_type))

    def _warn(self, message: str, node: ASTNode, warning_type: str = "SemanticWarning"):
        self.warnings.append(SemanticWarning(message=message, line=node.line, column=node.column, warning_type=warning_type))

    # -------------------------------------------------------------------------
    # Visitor Implementations: Statements
    # -------------------------------------------------------------------------

    def visit_program(self, node: Program):
        for stmt in node.statements:
            stmt.accept(self)

    def visit_var_decl(self, node: VarDecl):
        # 1. Check if type is a valid recognized type
        valid_types = {"int", "float", "string", "bool"}
        if node.var_type not in valid_types:
            self._error(f"Unknown data type '{node.var_type}'", node, "TypeError")

        # 2. Check for duplicate declaration in the current scope
        existing = self.symbol_table.lookup(node.name, current_scope_only=True)
        if existing is not None:
            self._error(
                f"Duplicate declaration of variable '{node.name}' (already declared at Line {existing.line}, Col {existing.column})",
                node,
                "DeclarationError"
            )
            return

        # 3. Check initializer expression if present
        is_init = False
        if node.initializer is not None:
            init_type = node.initializer.accept(self)
            if init_type and init_type != "unknown":
                if not self._is_type_compatible(node.var_type, init_type):
                    self._error(
                        f"Type mismatch: cannot initialize '{node.var_type}' variable '{node.name}' with expression of type '{init_type}'",
                        node,
                        "TypeError"
                    )
            is_init = True

        # 4. Define symbol in the current scope
        self.symbol_table.define(
            name=node.name,
            type_name=node.var_type,
            line=node.line,
            column=node.column,
            is_initialized=is_init
        )

    def visit_block(self, node: Block):
        self.symbol_table.enter_scope()
        for stmt in node.statements:
            stmt.accept(self)
        self.symbol_table.exit_scope()

    def visit_if_stmt(self, node: IfStmt):
        cond_type = node.condition.accept(self)
        if cond_type and cond_type not in ("bool", "int", "float", "any"):
            self._error(f"Condition in 'if' statement must evaluate to boolean or numeric, got '{cond_type}'", node.condition, "TypeError")

        node.then_branch.accept(self)
        if node.else_branch is not None:
            node.else_branch.accept(self)

    def visit_while_stmt(self, node: WhileStmt):
        cond_type = node.condition.accept(self)
        if cond_type and cond_type not in ("bool", "int", "float", "any"):
            self._error(f"Condition in 'while' loop must evaluate to boolean or numeric, got '{cond_type}'", node.condition, "TypeError")

        node.body.accept(self)

    def visit_for_stmt(self, node: ForStmt):
        self.symbol_table.enter_scope("for_loop")
        if node.init:
            node.init.accept(self)
        if node.condition:
            cond_type = node.condition.accept(self)
            if cond_type and cond_type not in ("bool", "int", "float", "any"):
                self._error(f"Condition in 'for' loop must evaluate to boolean or numeric, got '{cond_type}'", node.condition, "TypeError")
        if node.update:
            node.update.accept(self)

        node.body.accept(self)
        self.symbol_table.exit_scope()

    def visit_print_stmt(self, node: PrintStmt):
        for expr in node.expressions:
            expr.accept(self)

    def visit_return_stmt(self, node: ReturnStmt):
        ret_type = "void"
        if node.value is not None:
            ret_type = node.value.accept(self) or "void"

        if self.current_function_return_type:
            if not self._is_type_compatible(self.current_function_return_type, ret_type):
                self._error(
                    f"Return type mismatch: Function expects '{self.current_function_return_type}', got '{ret_type}'",
                    node,
                    "ReturnTypeError"
                )

    def visit_expr_stmt(self, node: ExprStmt):
        node.expression.accept(self)

    def visit_func_decl(self, node: FuncDecl):
        # Check duplicate function declaration
        existing = self.symbol_table.lookup(node.name, current_scope_only=True)
        if existing:
            self._error(f"Function '{node.name}' is already declared in current scope", node, "DeclarationError")

        # Define in enclosing scope
        self.symbol_table.define(
            name=node.name,
            type_name=node.return_type,
            line=node.line,
            column=node.column,
            is_initialized=True,
            extra={"params": node.params}
        )

        prev_return_type = self.current_function_return_type
        self.current_function_return_type = node.return_type

        # Enter function scope and define parameters
        self.symbol_table.enter_scope(f"func_{node.name}")
        for param_type, param_name in node.params:
            self.symbol_table.define(
                name=param_name,
                type_name=param_type,
                line=node.line,
                column=node.column,
                is_initialized=True
            )

        for stmt in node.body.statements:
            stmt.accept(self)

        self.symbol_table.exit_scope()
        self.current_function_return_type = prev_return_type

    # -------------------------------------------------------------------------
    # Visitor Implementations: Expressions (returning inferred types)
    # -------------------------------------------------------------------------

    def visit_literal_expr(self, node: LiteralExpr) -> str:
        return node.type_name

    def visit_identifier_expr(self, node: IdentifierExpr) -> str:
        sym = self.symbol_table.lookup(node.name)
        if sym is None:
            self._error(f"Undeclared identifier '{node.name}'", node, "UndeclaredVariableError")
            return "unknown"

        if not sym.is_initialized:
            self._warn(f"Variable '{node.name}' is read before being initialized", node, "UninitializedVariableWarning")

        return sym.type_name

    def visit_assign_expr(self, node: AssignExpr) -> str:
        sym = self.symbol_table.lookup(node.target)
        if sym is None:
            self._error(f"Undeclared variable '{node.target}' in assignment", node, "UndeclaredVariableError")
            # Analyze value expression anyway to catch nested errors
            node.value.accept(self)
            return "unknown"

        val_type = node.value.accept(self)
        if val_type and val_type != "unknown":
            if node.operator == "=":
                if not self._is_type_compatible(sym.type_name, val_type):
                    self._error(
                        f"Type mismatch: Cannot assign '{val_type}' expression to variable '{node.target}' of type '{sym.type_name}'",
                        node,
                        "TypeError"
                    )
            elif node.operator in ("+=", "-=", "*=", "/="):
                # Compound assignment type checking
                if node.operator == "+=" and sym.type_name == "string" and val_type == "string":
                    pass  # String concatenation allowed
                elif sym.type_name in ("int", "float") and val_type in ("int", "float"):
                    pass  # Numeric compound assignments allowed
                else:
                    self._error(
                        f"Operator '{node.operator}' is not supported between '{sym.type_name}' and '{val_type}'",
                        node,
                        "TypeError"
                    )

        # Mark as initialized
        self.symbol_table.mark_initialized(node.target)
        return sym.type_name

    def visit_binary_expr(self, node: BinaryExpr) -> str:
        lt = node.left.accept(self) or "unknown"
        rt = node.right.accept(self) or "unknown"

        if lt == "unknown" or rt == "unknown":
            return "unknown"

        op = node.operator

        # 1. Arithmetic Operators
        if op in ("+", "-", "*", "/", "%"):
            # String concatenation
            if op == "+" and (lt == "string" or rt == "string"):
                return "string"

            # Modulo requires integer operands
            if op == "%":
                if lt == "int" and rt == "int":
                    return "int"
                self._error(f"Operator '%' requires integer operands, got '{lt}' and '{rt}'", node, "TypeError")
                return "int"

            # Numeric arithmetic
            if lt in ("int", "float") and rt in ("int", "float"):
                if lt == "float" or rt == "float":
                    return "float"
                return "int"

            self._error(f"Operator '{op}' is not supported between types '{lt}' and '{rt}'", node, "TypeError")
            return "unknown"

        # 2. Relational Operators (<, <=, >, >=)
        if op in ("<", "<=", ">", ">="):
            if lt in ("int", "float") and rt in ("int", "float"):
                return "bool"
            if lt == "string" and rt == "string":
                return "bool"
            self._error(f"Relational operator '{op}' cannot compare types '{lt}' and '{rt}'", node, "TypeError")
            return "bool"

        # 3. Equality Operators (==, !=)
        if op in ("==", "!="):
            if (lt in ("int", "float") and rt in ("int", "float")) or (lt == rt):
                return "bool"
            self._error(f"Equality operator '{op}' cannot compare incompatible types '{lt}' and '{rt}'", node, "TypeError")
            return "bool"

        # 4. Logical Operators (&&, ||)
        if op in ("&&", "||"):
            if lt in ("bool", "int") and rt in ("bool", "int"):
                return "bool"
            self._error(f"Logical operator '{op}' requires boolean operands, got '{lt}' and '{rt}'", node, "TypeError")
            return "bool"

        return "unknown"

    def visit_unary_expr(self, node: UnaryExpr) -> str:
        op = node.operator
        operand_type = node.operand.accept(self) or "unknown"

        if operand_type == "unknown":
            return "unknown"

        if op == "!":
            if operand_type in ("bool", "int"):
                return "bool"
            self._error(f"Logical not operator '!' requires boolean operand, got '{operand_type}'", node, "TypeError")
            return "bool"

        if op in ("-", "+"):
            if operand_type in ("int", "float"):
                return operand_type
            self._error(f"Unary operator '{op}' requires numeric operand, got '{operand_type}'", node, "TypeError")
            return "unknown"

        return operand_type

    def visit_call_expr(self, node: CallExpr) -> str:
        sym = self.symbol_table.lookup(node.callee)
        if sym is None:
            self._error(f"Call to undeclared function '{node.callee}'", node, "UndeclaredFunctionError")
            for arg in node.args:
                arg.accept(self)
            return "unknown"

        # Validate argument count if metadata is present
        if sym.extra and "params" in sym.extra:
            expected_params = sym.extra["params"]
            if len(node.args) != len(expected_params):
                self._error(
                    f"Function '{node.callee}' expects {len(expected_params)} arguments, got {len(node.args)}",
                    node,
                    "ArgumentCountError"
                )

        for arg in node.args:
            arg.accept(self)

        return sym.type_name

    def visit_group_expr(self, node: GroupExpr) -> str:
        return node.expression.accept(self)
