"""
tac_generator.py
================
Three-Address Code (TAC) Intermediate Representation (IR) generator for EduScript.
Translates the validated AST into linear Three-Address Code instructions.

Features:
- Emits atomic 3-address instructions (Binary, Unary, Assign, Control Flow, Jumps, Labels, IO).
- Generates unique temporary registers (t0, t1, t2...) and jump labels (L0, L1, L2...).
- Provides clean formatted IR listings with line numbers for Compiler Design vivas and debugging.
"""

from dataclasses import dataclass
from typing import List, Optional, Any, Union

from ast_nodes import (
    ASTVisitor, ASTNode, Program, Stmt, Expr,
    VarDecl, Block, IfStmt, WhileStmt, ForStmt,
    PrintStmt, ReturnStmt, ExprStmt, FuncDecl,
    LiteralExpr, IdentifierExpr, BinaryExpr, UnaryExpr,
    AssignExpr, CallExpr, GroupExpr
)


@dataclass
class TACInstruction:
    """
    Represents a single Three-Address Code instruction.

    Attributes:
        op: Opcode (e.g. 'ASSIGN', 'ADD', 'SUB', 'MUL', 'DIV', 'LABEL', 'GOTO', 'IF_FALSE', 'PRINT', etc.).
        arg1: First operand / argument (or None).
        arg2: Second operand (or None).
        result: Target variable / register / label name (or None).
        line: Source code line for mapping IR back to source.
    """
    op: str
    arg1: Optional[Any] = None
    arg2: Optional[Any] = None
    result: Optional[Any] = None
    line: int = 1

    def __str__(self) -> str:
        """User-friendly 3-Address Code string representation."""
        op_map = {
            "ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "MOD": "%",
            "EQ": "==", "NEQ": "!=", "LT": "<", "LE": "<=", "GT": ">", "GE": ">=",
            "AND": "&&", "OR": "||"
        }

        if self.op == "LABEL":
            return f"LABEL {self.result}:"
        elif self.op == "GOTO":
            return f"goto {self.result}"
        elif self.op == "IF_FALSE":
            return f"if_false {self.arg1} goto {self.result}"
        elif self.op == "IF_TRUE":
            return f"if_true {self.arg1} goto {self.result}"
        elif self.op == "ASSIGN":
            val_str = repr(self.arg1) if isinstance(self.arg1, str) and not self.arg1.startswith(("t", "@", "$")) and " " in self.arg1 else str(self.arg1)
            return f"{self.result} = {val_str}"
        elif self.op in op_map:
            return f"{self.result} = {self.arg1} {op_map[self.op]} {self.arg2}"
        elif self.op == "NEG":
            return f"{self.result} = -{self.arg1}"
        elif self.op == "NOT":
            return f"{self.result} = !{self.arg1}"
        elif self.op == "PRINT":
            return f"print {self.arg1}"
        elif self.op == "RETURN":
            return f"return {self.arg1}" if self.arg1 is not None else "return"
        elif self.op == "PARAM":
            return f"param {self.arg1}"
        elif self.op == "CALL":
            return f"{self.result} = call {self.arg1}, {self.arg2}"
        return f"{self.op} {self.arg1}, {self.arg2} -> {self.result}"


class TACProgram:
    """Container for a sequence of TAC instructions with utility formatters."""

    def __init__(self, instructions: List[TACInstruction]):
        self.instructions = instructions

    def format_listing(self) -> str:
        """Formats the TAC program into a numbered instruction list."""
        if not self.instructions:
            return "(Empty TAC Program)"

        lines = []
        lines.append("=" * 60)
        lines.append(f"{'INDEX':<8} | {'INSTRUCTION':<48}")
        lines.append("=" * 60)

        for idx, instr in enumerate(self.instructions):
            if instr.op == "LABEL":
                lines.append(f"{idx:<8} | {str(instr)}")
            else:
                lines.append(f"{idx:<8} |   {str(instr)}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.format_listing()


class TACGenerator(ASTVisitor):
    """
    Translates AST into Three-Address Code (TAC).
    """

    OPCODE_MAP = {
        "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
        "==": "EQ", "!=": "NEQ", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE",
        "&&": "AND", "||": "OR"
    }

    def __init__(self):
        self.instructions: List[TACInstruction] = []
        self._temp_counter = 0
        self._label_counter = 0

    def generate(self, program: Program) -> TACProgram:
        """
        Translates a Program AST into a TACProgram.
        """
        self.instructions = []
        self._temp_counter = 0
        self._label_counter = 0
        program.accept(self)
        return TACProgram(self.instructions)

    # -------------------------------------------------------------------------
    # Helper Generator Methods
    # -------------------------------------------------------------------------

    def _new_temp(self) -> str:
        """Generates a new temporary variable (t0, t1, t2...)."""
        t = f"t{self._temp_counter}"
        self._temp_counter += 1
        return t

    def _new_label(self, prefix: str = "L") -> str:
        """Generates a new branch label (L0, L1, L2...)."""
        lbl = f"{prefix}{self._label_counter}"
        self._label_counter += 1
        return lbl

    def _emit(self, op: str, arg1: Optional[Any] = None, arg2: Optional[Any] = None, result: Optional[Any] = None, line: int = 1):
        self.instructions.append(TACInstruction(op=op, arg1=arg1, arg2=arg2, result=result, line=line))

    # -------------------------------------------------------------------------
    # Visitor Implementations: Statements
    # -------------------------------------------------------------------------

    def visit_program(self, node: Program):
        for stmt in node.statements:
            stmt.accept(self)

    def visit_var_decl(self, node: VarDecl):
        if node.initializer is not None:
            val_temp = node.initializer.accept(self)
            self._emit("ASSIGN", arg1=val_temp, result=node.name, line=node.line)

    def visit_block(self, node: Block):
        for stmt in node.statements:
            stmt.accept(self)

    def visit_if_stmt(self, node: IfStmt):
        cond_temp = node.condition.accept(self)
        else_label = self._new_label("L_else_")
        end_label = self._new_label("L_end_if_")

        if node.else_branch is not None:
            self._emit("IF_FALSE", arg1=cond_temp, result=else_label, line=node.line)
            node.then_branch.accept(self)
            self._emit("GOTO", result=end_label, line=node.line)
            self._emit("LABEL", result=else_label, line=node.line)
            node.else_branch.accept(self)
            self._emit("LABEL", result=end_label, line=node.line)
        else:
            self._emit("IF_FALSE", arg1=cond_temp, result=end_label, line=node.line)
            node.then_branch.accept(self)
            self._emit("LABEL", result=end_label, line=node.line)

    def visit_while_stmt(self, node: WhileStmt):
        start_label = self._new_label("L_while_start_")
        end_label = self._new_label("L_while_end_")

        self._emit("LABEL", result=start_label, line=node.line)
        cond_temp = node.condition.accept(self)
        self._emit("IF_FALSE", arg1=cond_temp, result=end_label, line=node.line)

        node.body.accept(self)

        self._emit("GOTO", result=start_label, line=node.line)
        self._emit("LABEL", result=end_label, line=node.line)

    def visit_for_stmt(self, node: ForStmt):
        if node.init:
            node.init.accept(self)

        start_label = self._new_label("L_for_start_")
        end_label = self._new_label("L_for_end_")

        self._emit("LABEL", result=start_label, line=node.line)

        if node.condition:
            cond_temp = node.condition.accept(self)
            self._emit("IF_FALSE", arg1=cond_temp, result=end_label, line=node.line)

        node.body.accept(self)

        if node.update:
            node.update.accept(self)

        self._emit("GOTO", result=start_label, line=node.line)
        self._emit("LABEL", result=end_label, line=node.line)

    def visit_print_stmt(self, node: PrintStmt):
        for expr in node.expressions:
            val_temp = expr.accept(self)
            self._emit("PRINT", arg1=val_temp, line=node.line)

    def visit_return_stmt(self, node: ReturnStmt):
        val_temp = None
        if node.value is not None:
            val_temp = node.value.accept(self)
        self._emit("RETURN", arg1=val_temp, line=node.line)

    def visit_expr_stmt(self, node: ExprStmt):
        node.expression.accept(self)

    def visit_func_decl(self, node: FuncDecl):
        func_label = f"func_{node.name}"
        self._emit("LABEL", result=func_label, line=node.line)
        node.body.accept(self)
        # Ensure implicit return if none at end
        self._emit("RETURN", arg1=None, line=node.line)

    # -------------------------------------------------------------------------
    # Visitor Implementations: Expressions (returning operand address/temp)
    # -------------------------------------------------------------------------

    def visit_literal_expr(self, node: LiteralExpr) -> Any:
        return node.value

    def visit_identifier_expr(self, node: IdentifierExpr) -> str:
        return node.name

    def visit_assign_expr(self, node: AssignExpr) -> str:
        val_temp = node.value.accept(self)
        if node.operator == "=":
            self._emit("ASSIGN", arg1=val_temp, result=node.target, line=node.line)
            return node.target
        else:
            # Compound assignment (+=, -=, *=, /=)
            base_op = node.operator[:-1]  # '+', '-', '*', '/'
            opcode = self.OPCODE_MAP[base_op]
            temp = self._new_temp()
            self._emit(opcode, arg1=node.target, arg2=val_temp, result=temp, line=node.line)
            self._emit("ASSIGN", arg1=temp, result=node.target, line=node.line)
            return node.target

    def visit_binary_expr(self, node: BinaryExpr) -> str:
        left_temp = node.left.accept(self)
        right_temp = node.right.accept(self)
        opcode = self.OPCODE_MAP.get(node.operator, "BINARY")
        res_temp = self._new_temp()
        self._emit(opcode, arg1=left_temp, arg2=right_temp, result=res_temp, line=node.line)
        return res_temp

    def visit_unary_expr(self, node: UnaryExpr) -> str:
        operand_temp = node.operand.accept(self)
        res_temp = self._new_temp()
        if node.operator == "-":
            self._emit("NEG", arg1=operand_temp, result=res_temp, line=node.line)
        elif node.operator == "!":
            self._emit("NOT", arg1=operand_temp, result=res_temp, line=node.line)
        elif node.operator == "+":
            return operand_temp
        return res_temp

    def visit_call_expr(self, node: CallExpr) -> str:
        arg_temps = []
        for arg in node.args:
            arg_temps.append(arg.accept(self))
        for at in arg_temps:
            self._emit("PARAM", arg1=at, line=node.line)
        res_temp = self._new_temp()
        self._emit("CALL", arg1=node.callee, arg2=len(arg_temps), result=res_temp, line=node.line)
        return res_temp

    def visit_group_expr(self, node: GroupExpr) -> Any:
        return node.expression.accept(self)
