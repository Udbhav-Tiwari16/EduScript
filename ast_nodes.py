"""
ast_nodes.py
============
Abstract Syntax Tree (AST) node definitions and hierarchy for EduScript.
Part of the Syntax Analysis stage in the Compiler pipeline.

Provides:
- Strongly-typed AST nodes with source position tracking (line, column).
- Visitor pattern interface for traversals (Semantic Analysis, TAC Generation, AST Interpretation).
- Built-in ASTPrinter for visual tree display (ASCII box/branch format).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


class ASTVisitor(ABC):
    """Abstract base class for AST visitors."""

    @abstractmethod
    def visit_program(self, node: "Program") -> Any: ...

    @abstractmethod
    def visit_var_decl(self, node: "VarDecl") -> Any: ...

    @abstractmethod
    def visit_block(self, node: "Block") -> Any: ...

    @abstractmethod
    def visit_if_stmt(self, node: "IfStmt") -> Any: ...

    @abstractmethod
    def visit_while_stmt(self, node: "WhileStmt") -> Any: ...

    @abstractmethod
    def visit_for_stmt(self, node: "ForStmt") -> Any: ...

    @abstractmethod
    def visit_print_stmt(self, node: "PrintStmt") -> Any: ...

    @abstractmethod
    def visit_return_stmt(self, node: "ReturnStmt") -> Any: ...

    @abstractmethod
    def visit_expr_stmt(self, node: "ExprStmt") -> Any: ...

    @abstractmethod
    def visit_func_decl(self, node: "FuncDecl") -> Any: ...

    @abstractmethod
    def visit_literal_expr(self, node: "LiteralExpr") -> Any: ...

    @abstractmethod
    def visit_identifier_expr(self, node: "IdentifierExpr") -> Any: ...

    @abstractmethod
    def visit_binary_expr(self, node: "BinaryExpr") -> Any: ...

    @abstractmethod
    def visit_unary_expr(self, node: "UnaryExpr") -> Any: ...

    @abstractmethod
    def visit_assign_expr(self, node: "AssignExpr") -> Any: ...

    @abstractmethod
    def visit_call_expr(self, node: "CallExpr") -> Any: ...

    @abstractmethod
    def visit_group_expr(self, node: "GroupExpr") -> Any: ...


@dataclass
class ASTNode(ABC):
    """Base class for all AST nodes."""
    line: int = 1
    column: int = 1

    def accept(self, visitor: ASTVisitor) -> Any:
        method_name = f"visit_{self.__class__.__name__.lower()}"
        visitor_fn = getattr(visitor, method_name, None)
        if visitor_fn:
            return visitor_fn(self)
        raise NotImplementedError(f"Visitor {visitor.__class__.__name__} has no method {method_name}")


# -----------------------------------------------------------------------------
# Expressions
# -----------------------------------------------------------------------------

@dataclass
class Expr(ASTNode):
    """Base class for expression nodes."""
    pass


@dataclass
class LiteralExpr(Expr):
    """Represents a literal value: integer, float, string, or boolean."""
    value: Any = None
    type_name: str = "int"  # 'int', 'float', 'string', 'bool'

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_literal_expr(self)


@dataclass
class IdentifierExpr(Expr):
    """Represents a variable identifier usage."""
    name: str = ""

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_identifier_expr(self)


@dataclass
class BinaryExpr(Expr):
    """Represents a binary operation: left OP right."""
    left: Expr = field(default_factory=Expr)
    operator: str = "+"
    right: Expr = field(default_factory=Expr)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_binary_expr(self)


@dataclass
class UnaryExpr(Expr):
    """Represents a unary operation: OP operand."""
    operator: str = "-"
    operand: Expr = field(default_factory=Expr)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_unary_expr(self)


@dataclass
class AssignExpr(Expr):
    """Represents an assignment or compound assignment expression."""
    target: str = ""
    operator: str = "="  # '=', '+=', '-=', '*=', '/='
    value: Expr = field(default_factory=Expr)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_assign_expr(self)


@dataclass
class CallExpr(Expr):
    """Represents a function call expression."""
    callee: str = ""
    args: List[Expr] = field(default_factory=list)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_call_expr(self)


@dataclass
class GroupExpr(Expr):
    """Represents a parenthesized expression."""
    expression: Expr = field(default_factory=Expr)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_group_expr(self)


# -----------------------------------------------------------------------------
# Statements
# -----------------------------------------------------------------------------

@dataclass
class Stmt(ASTNode):
    """Base class for statement nodes."""
    pass


@dataclass
class Program(ASTNode):
    """Root node of the EduScript AST."""
    statements: List[Stmt] = field(default_factory=list)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_program(self)


@dataclass
class VarDecl(Stmt):
    """Represents a variable declaration statement (e.g. int count = 5;)."""
    var_type: str = "int"  # 'int', 'float', 'string', 'bool'
    name: str = ""
    initializer: Optional[Expr] = None

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_var_decl(self)


@dataclass
class Block(Stmt):
    """Represents a scoped block of statements enclosed in braces { ... }."""
    statements: List[Stmt] = field(default_factory=list)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_block(self)


@dataclass
class IfStmt(Stmt):
    """Represents an if/else conditional branch."""
    condition: Expr = field(default_factory=Expr)
    then_branch: Stmt = field(default_factory=Stmt)
    else_branch: Optional[Stmt] = None

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_if_stmt(self)


@dataclass
class WhileStmt(Stmt):
    """Represents a while loop."""
    condition: Expr = field(default_factory=Expr)
    body: Stmt = field(default_factory=Stmt)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_while_stmt(self)


@dataclass
class ForStmt(Stmt):
    """Represents a for loop: for (init; cond; update) body."""
    init: Optional[Stmt] = None
    condition: Optional[Expr] = None
    update: Optional[Expr] = None
    body: Stmt = field(default_factory=Stmt)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_for_stmt(self)


@dataclass
class PrintStmt(Stmt):
    """Represents a print statement: print(expr1, expr2, ...);"""
    expressions: List[Expr] = field(default_factory=list)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_print_stmt(self)


@dataclass
class ReturnStmt(Stmt):
    """Represents a return statement: return expr;"""
    value: Optional[Expr] = None

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_return_stmt(self)


@dataclass
class ExprStmt(Stmt):
    """Represents an expression evaluated as a statement."""
    expression: Expr = field(default_factory=Expr)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_expr_stmt(self)


@dataclass
class FuncDecl(Stmt):
    """Represents a function definition."""
    return_type: str = "void"
    name: str = ""
    params: List[Tuple[str, str]] = field(default_factory=list)  # (type, name)
    body: Block = field(default_factory=Block)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_func_decl(self)


# -----------------------------------------------------------------------------
# AST Pretty Printer
# -----------------------------------------------------------------------------

class ASTPrinter(ASTVisitor):
    """
    Renders an AST into a formatted hierarchical ASCII tree.
    Useful for Compiler Design debugging, lab vivas, and CLI visualization.
    """

    def print(self, node: ASTNode) -> str:
        lines: List[str] = []
        self._format_node(node, "", True, lines)
        return "\n".join(lines)

    def _format_node(self, node: Any, prefix: str, is_last: bool, lines: List[str]):
        branch = "\\-- " if is_last else "+-- "
        next_prefix = prefix + ("    " if is_last else "|   ")

        if node is None:
            lines.append(f"{prefix}{branch}None")
            return

        if not isinstance(node, ASTNode):
            lines.append(f"{prefix}{branch}{node}")
            return

        # Header for the node
        label = self._node_label(node)
        lines.append(f"{prefix}{branch}{label}")

        children = self._get_children(node)
        for i, child in enumerate(children):
            self._format_node(child, next_prefix, i == len(children) - 1, lines)

    def _node_label(self, node: ASTNode) -> str:
        loc = f"[{node.line}:{node.column}]"
        if isinstance(node, Program):
            return f"Program {loc}"
        elif isinstance(node, VarDecl):
            return f"VarDecl<{node.var_type}>: '{node.name}' {loc}"
        elif isinstance(node, Block):
            return f"Block ({len(node.statements)} stmts) {loc}"
        elif isinstance(node, IfStmt):
            return f"IfStmt {loc}"
        elif isinstance(node, WhileStmt):
            return f"WhileStmt {loc}"
        elif isinstance(node, ForStmt):
            return f"ForStmt {loc}"
        elif isinstance(node, PrintStmt):
            return f"PrintStmt {loc}"
        elif isinstance(node, ReturnStmt):
            return f"ReturnStmt {loc}"
        elif isinstance(node, ExprStmt):
            return f"ExprStmt {loc}"
        elif isinstance(node, FuncDecl):
            param_str = ", ".join(f"{t} {n}" for t, n in node.params)
            return f"FuncDecl<{node.return_type}> {node.name}({param_str}) {loc}"
        elif isinstance(node, LiteralExpr):
            return f"Literal<{node.type_name}>: {node.value!r} {loc}"
        elif isinstance(node, IdentifierExpr):
            return f"Identifier: '{node.name}' {loc}"
        elif isinstance(node, BinaryExpr):
            return f"BinaryOp: '{node.operator}' {loc}"
        elif isinstance(node, UnaryExpr):
            return f"UnaryOp: '{node.operator}' {loc}"
        elif isinstance(node, AssignExpr):
            return f"Assign: '{node.target}' {node.operator} {loc}"
        elif isinstance(node, CallExpr):
            return f"Call: '{node.callee}()' {loc}"
        elif isinstance(node, GroupExpr):
            return f"Group () {loc}"
        return f"{node.__class__.__name__} {loc}"

    def _get_children(self, node: ASTNode) -> List[Any]:
        if isinstance(node, Program):
            return list(node.statements)
        elif isinstance(node, VarDecl):
            return [node.initializer] if node.initializer is not None else []
        elif isinstance(node, Block):
            return list(node.statements)
        elif isinstance(node, IfStmt):
            children = [node.condition, node.then_branch]
            if node.else_branch:
                children.append(node.else_branch)
            return children
        elif isinstance(node, WhileStmt):
            return [node.condition, node.body]
        elif isinstance(node, ForStmt):
            children = []
            if node.init: children.append(node.init)
            if node.condition: children.append(node.condition)
            if node.update: children.append(node.update)
            children.append(node.body)
            return children
        elif isinstance(node, PrintStmt):
            return list(node.expressions)
        elif isinstance(node, ReturnStmt):
            return [node.value] if node.value is not None else []
        elif isinstance(node, ExprStmt):
            return [node.expression]
        elif isinstance(node, FuncDecl):
            return [node.body]
        elif isinstance(node, BinaryExpr):
            return [node.left, node.right]
        elif isinstance(node, UnaryExpr):
            return [node.operand]
        elif isinstance(node, AssignExpr):
            return [node.value]
        elif isinstance(node, CallExpr):
            return list(node.args)
        elif isinstance(node, GroupExpr):
            return [node.expression]
        return []

    # Visitor stub implementations
    def visit_program(self, node: Program): return self.print(node)
    def visit_var_decl(self, node: VarDecl): return self.print(node)
    def visit_block(self, node: Block): return self.print(node)
    def visit_if_stmt(self, node: IfStmt): return self.print(node)
    def visit_while_stmt(self, node: WhileStmt): return self.print(node)
    def visit_for_stmt(self, node: ForStmt): return self.print(node)
    def visit_print_stmt(self, node: PrintStmt): return self.print(node)
    def visit_return_stmt(self, node: ReturnStmt): return self.print(node)
    def visit_expr_stmt(self, node: ExprStmt): return self.print(node)
    def visit_func_decl(self, node: FuncDecl): return self.print(node)
    def visit_literal_expr(self, node: LiteralExpr): return self.print(node)
    def visit_identifier_expr(self, node: IdentifierExpr): return self.print(node)
    def visit_binary_expr(self, node: BinaryExpr): return self.print(node)
    def visit_unary_expr(self, node: UnaryExpr): return self.print(node)
    def visit_assign_expr(self, node: AssignExpr): return self.print(node)
    def visit_call_expr(self, node: CallExpr): return self.print(node)
    def visit_group_expr(self, node: GroupExpr): return self.print(node)
