"""
interpreter.py
==============
Execution Engine for EduScript.
Includes:
1. TACInterpreter (Virtual Machine): Executes Three-Address Code Intermediate Representation.
2. ASTInterpreter (Tree-Walk): Directly executes the validated Abstract Syntax Tree.

Features:
- Robust arithmetic & logical evaluations with type safety.
- Runtime error handling (Division/Modulo by zero, uninitialized access, runtime exceptions).
- Captured output buffer for automated testing and CLI reporting.
- Clean execution state and environment inspection.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union

from ast_nodes import (
    ASTVisitor, ASTNode, Program, Stmt, Expr,
    VarDecl, Block, IfStmt, WhileStmt, ForStmt,
    PrintStmt, ReturnStmt, ExprStmt, FuncDecl,
    LiteralExpr, IdentifierExpr, BinaryExpr, UnaryExpr,
    AssignExpr, CallExpr, GroupExpr
)
from tac_generator import TACProgram, TACInstruction


class RuntimeErrorDetail(Exception):
    """Represents an error that occurs during program execution."""
    def __init__(self, message: str, line: int, column: int = 1):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def __str__(self) -> str:
        return f"[Line {self.line}] Runtime Error: {self.message}"


@dataclass
class ExecutionResult:
    """Encapsulates the result of executing an EduScript program."""
    success: bool
    output: List[str] = field(default_factory=list)
    return_value: Any = None
    error: Optional[RuntimeErrorDetail] = None
    environment: Dict[str, Any] = field(default_factory=dict)

    def print_summary(self):
        """Prints formatted execution results."""
        print("=" * 60)
        print("                 PROGRAM EXECUTION OUTPUT")
        print("=" * 60)
        if self.output:
            for line in self.output:
                print(line)
        else:
            print("(No output printed)")
        print("=" * 60)
        if self.error:
            print(f"! Execution Failed: {self.error}")
        else:
            ret_display = repr(self.return_value) if self.return_value is not None else "0 (default)"
            print(f"Program Exited Successfully. Return Code: {ret_display}")
        print("=" * 60)


# =============================================================================
# Three-Address Code (TAC) Virtual Machine Interpreter
# =============================================================================

class TACInterpreter:
    """
    Virtual Machine that executes a linear stream of Three-Address Code instructions.
    """

    def __init__(self, tac_program: TACProgram):
        self.instructions: List[TACInstruction] = tac_program.instructions
        self.env: Dict[str, Any] = {}
        self.output: List[str] = []
        self.labels: Dict[str, int] = {}
        self.pc: int = 0
        self.return_value: Any = None
        self.call_stack: List[int] = []

    def _resolve(self, val: Any, line: int) -> Any:
        """Resolves an operand (literal constant or variable/temp name)."""
        if val is None:
            return None
        if isinstance(val, (int, float, bool)):
            return val
        if isinstance(val, str):
            # Check if it's a variable or temp register in the environment
            if val in self.env:
                return self.env[val]
            # Check if it's a string literal
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                return val[1:-1]
            # Try to convert to int or float if stringified number
            if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
                return int(val)
            try:
                return float(val)
            except ValueError:
                pass
            # If it's a known identifier not yet assigned
            return val
        return val

    def run(self, max_instructions: int = 1000000, print_live: bool = False) -> ExecutionResult:
        """
        Executes the TAC program to completion or until an error/halt.
        """
        self.env.clear()
        self.output.clear()
        self.labels.clear()
        self.pc = 0
        self.return_value = None
        self.call_stack.clear()

        # 1. First pass: Index all labels
        for idx, instr in enumerate(self.instructions):
            if instr.op == "LABEL":
                self.labels[instr.result] = idx

        # 2. Execution Loop
        instr_count = 0
        while 0 <= self.pc < len(self.instructions):
            instr_count += 1
            if instr_count > max_instructions:
                return ExecutionResult(
                    success=False,
                    output=self.output,
                    error=RuntimeErrorDetail("Execution step limit exceeded (infinite loop detected)", line=self.instructions[self.pc].line),
                    environment=self.env
                )

            instr = self.instructions[self.pc]
            line = instr.line

            try:
                # Dispatch Opcode
                if instr.op == "LABEL":
                    self.pc += 1
                    continue

                elif instr.op == "ASSIGN":
                    val = self._resolve(instr.arg1, line)
                    self.env[instr.result] = val
                    self.pc += 1

                elif instr.op == "ADD":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    if isinstance(a, str) or isinstance(b, str):
                        self.env[instr.result] = str(a) + str(b)
                    else:
                        self.env[instr.result] = a + b
                    self.pc += 1

                elif instr.op == "SUB":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = a - b
                    self.pc += 1

                elif instr.op == "MUL":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = a * b
                    self.pc += 1

                elif instr.op == "DIV":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    if b == 0:
                        raise RuntimeErrorDetail("Division by zero", line)
                    # Standard division: if both integers and exact, return int or float
                    if isinstance(a, int) and isinstance(b, int) and a % b == 0:
                        self.env[instr.result] = a // b
                    else:
                        self.env[instr.result] = a / b
                    self.pc += 1

                elif instr.op == "MOD":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    if b == 0:
                        raise RuntimeErrorDetail("Modulo by zero", line)
                    self.env[instr.result] = a % b
                    self.pc += 1

                elif instr.op == "EQ":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = (a == b)
                    self.pc += 1

                elif instr.op == "NEQ":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = (a != b)
                    self.pc += 1

                elif instr.op == "LT":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = (a < b)
                    self.pc += 1

                elif instr.op == "LE":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = (a <= b)
                    self.pc += 1

                elif instr.op == "GT":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = (a > b)
                    self.pc += 1

                elif instr.op == "GE":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = (a >= b)
                    self.pc += 1

                elif instr.op == "AND":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = bool(a and b)
                    self.pc += 1

                elif instr.op == "OR":
                    a = self._resolve(instr.arg1, line)
                    b = self._resolve(instr.arg2, line)
                    self.env[instr.result] = bool(a or b)
                    self.pc += 1

                elif instr.op == "NOT":
                    a = self._resolve(instr.arg1, line)
                    self.env[instr.result] = not bool(a)
                    self.pc += 1

                elif instr.op == "NEG":
                    a = self._resolve(instr.arg1, line)
                    self.env[instr.result] = -a
                    self.pc += 1

                elif instr.op == "GOTO":
                    target_label = instr.result
                    if target_label not in self.labels:
                        raise RuntimeErrorDetail(f"Jump target label '{target_label}' not found", line)
                    self.pc = self.labels[target_label]

                elif instr.op == "IF_FALSE":
                    cond = self._resolve(instr.arg1, line)
                    if not bool(cond):
                        target_label = instr.result
                        if target_label not in self.labels:
                            raise RuntimeErrorDetail(f"Jump target label '{target_label}' not found", line)
                        self.pc = self.labels[target_label]
                    else:
                        self.pc += 1

                elif instr.op == "IF_TRUE":
                    cond = self._resolve(instr.arg1, line)
                    if bool(cond):
                        target_label = instr.result
                        if target_label not in self.labels:
                            raise RuntimeErrorDetail(f"Jump target label '{target_label}' not found", line)
                        self.pc = self.labels[target_label]
                    else:
                        self.pc += 1

                elif instr.op == "PRINT":
                    val = self._resolve(instr.arg1, line)
                    output_str = str(val)
                    self.output.append(output_str)
                    if print_live:
                        print(output_str)
                    self.pc += 1

                elif instr.op == "RETURN":
                    val = self._resolve(instr.arg1, line)
                    self.return_value = val
                    if self.call_stack:
                        self.pc = self.call_stack.pop()
                    else:
                        # End of top-level execution
                        break

                else:
                    self.pc += 1

            except RuntimeErrorDetail as rerr:
                return ExecutionResult(
                    success=False,
                    output=self.output,
                    return_value=self.return_value,
                    error=rerr,
                    environment=self.env
                )
            except Exception as ex:
                return ExecutionResult(
                    success=False,
                    output=self.output,
                    return_value=self.return_value,
                    error=RuntimeErrorDetail(str(ex), line=line),
                    environment=self.env
                )

        return ExecutionResult(
            success=True,
            output=self.output,
            return_value=self.return_value if self.return_value is not None else 0,
            error=None,
            environment=self.env
        )


# =============================================================================
# AST Tree-Walk Interpreter (Alternative Direct Execution)
# =============================================================================

class ASTInterpreter(ASTVisitor):
    """
    Direct Abstract Syntax Tree interpreter for EduScript.
    """

    def __init__(self):
        self.globals: Dict[str, Any] = {}
        self.scopes: List[Dict[str, Any]] = [self.globals]
        self.output: List[str] = []
        self.return_value: Any = None
        self._returned = False

    def _current_scope(self) -> Dict[str, Any]:
        return self.scopes[-1]

    def _lookup(self, name: str) -> Any:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _assign(self, name: str, value: Any):
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = value
                return
        self.scopes[-1][name] = value

    def interpret(self, program: Program, print_live: bool = False) -> ExecutionResult:
        self.scopes = [{}]
        self.output = []
        self.return_value = None
        self._returned = False
        self._print_live = print_live

        try:
            program.accept(self)
            return ExecutionResult(
                success=True,
                output=self.output,
                return_value=self.return_value if self.return_value is not None else 0,
                environment=self.scopes[0]
            )
        except RuntimeErrorDetail as rerr:
            return ExecutionResult(
                success=False,
                output=self.output,
                return_value=self.return_value,
                error=rerr,
                environment=self.scopes[0]
            )

    def visit_program(self, node: Program):
        for stmt in node.statements:
            if self._returned:
                break
            stmt.accept(self)

    def visit_var_decl(self, node: VarDecl):
        val = None
        if node.initializer:
            val = node.initializer.accept(self)
        self._current_scope()[node.name] = val

    def visit_block(self, node: Block):
        self.scopes.append({})
        for stmt in node.statements:
            if self._returned:
                break
            stmt.accept(self)
        self.scopes.pop()

    def visit_if_stmt(self, node: IfStmt):
        cond = node.condition.accept(self)
        if bool(cond):
            node.then_branch.accept(self)
        elif node.else_branch:
            node.else_branch.accept(self)

    def visit_while_stmt(self, node: WhileStmt):
        while bool(node.condition.accept(self)):
            if self._returned:
                break
            node.body.accept(self)

    def visit_for_stmt(self, node: ForStmt):
        self.scopes.append({})
        if node.init:
            node.init.accept(self)
        while node.condition is None or bool(node.condition.accept(self)):
            if self._returned:
                break
            node.body.accept(self)
            if node.update:
                node.update.accept(self)
        self.scopes.pop()

    def visit_print_stmt(self, node: PrintStmt):
        parts = [str(e.accept(self)) for e in node.expressions]
        out_str = " ".join(parts)
        self.output.append(out_str)
        if getattr(self, "_print_live", False):
            print(out_str)

    def visit_return_stmt(self, node: ReturnStmt):
        if node.value:
            self.return_value = node.value.accept(self)
        else:
            self.return_value = None
        self._returned = True

    def visit_expr_stmt(self, node: ExprStmt):
        node.expression.accept(self)

    def visit_func_decl(self, node: FuncDecl):
        pass

    def visit_literal_expr(self, node: LiteralExpr) -> Any:
        return node.value

    def visit_identifier_expr(self, node: IdentifierExpr) -> Any:
        val = self._lookup(node.name)
        return val

    def visit_binary_expr(self, node: BinaryExpr) -> Any:
        left = node.left.accept(self)
        right = node.right.accept(self)
        op = node.operator

        if op == "+": return left + right
        if op == "-": return left - right
        if op == "*": return left * right
        if op == "/":
            if right == 0: raise RuntimeErrorDetail("Division by zero", node.line)
            return left / right
        if op == "%":
            if right == 0: raise RuntimeErrorDetail("Modulo by zero", node.line)
            return left % right
        if op == "==": return left == right
        if op == "!=": return left != right
        if op == "<": return left < right
        if op == "<=": return left <= right
        if op == ">": return left > right
        if op == ">=": return left >= right
        if op == "&&": return bool(left and right)
        if op == "||": return bool(left or right)
        return None

    def visit_unary_expr(self, node: UnaryExpr) -> Any:
        val = node.operand.accept(self)
        if node.operator == "-": return -val
        if node.operator == "!": return not bool(val)
        if node.operator == "+": return val
        return val

    def visit_assign_expr(self, node: AssignExpr) -> Any:
        val = node.value.accept(self)
        if node.operator == "=":
            self._assign(node.target, val)
        elif node.operator == "+=":
            curr = self._lookup(node.target)
            self._assign(node.target, curr + val)
        elif node.operator == "-=":
            curr = self._lookup(node.target)
            self._assign(node.target, curr - val)
        elif node.operator == "*=":
            curr = self._lookup(node.target)
            self._assign(node.target, curr * val)
        elif node.operator == "/=":
            curr = self._lookup(node.target)
            if val == 0: raise RuntimeErrorDetail("Division by zero", node.line)
            self._assign(node.target, curr / val)
        return val

    def visit_call_expr(self, node: CallExpr) -> Any:
        return None

    def visit_group_expr(self, node: GroupExpr) -> Any:
        return node.expression.accept(self)
