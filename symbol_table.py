"""
symbol_table.py
===============
Scoped Symbol Table implementation for EduScript.
Maintains symbol information (type, scope level, declaration location, initialization status)
and manages hierarchical nested lexical scopes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class Symbol:
    """
    Represents a declared symbol (variable, constant, or function).

    Attributes:
        name: Identifier name.
        type_name: Data type ('int', 'float', 'string', 'bool', 'void', etc.).
        scope_level: Nesting depth of the scope (0 for global).
        line: Source code declaration line.
        column: Source code declaration column.
        is_initialized: True if an initial value has been assigned.
        extra: Additional metadata (e.g. parameter types for functions).
    """
    name: str
    type_name: str
    scope_level: int
    line: int
    column: int
    is_initialized: bool = False
    extra: Optional[Dict[str, Any]] = None

    def __repr__(self) -> str:
        init_str = "initialized" if self.is_initialized else "uninitialized"
        return f"Symbol(name='{self.name}', type='{self.type_name}', scope={self.scope_level}, {init_str}, loc={self.line}:{self.column})"


class Scope:
    """
    Represents a single lexical scope environment.
    """

    def __init__(self, name: str, level: int, parent: Optional["Scope"] = None):
        self.name = name
        self.level = level
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.children: List["Scope"] = []

    def define(self, symbol: Symbol) -> bool:
        """
        Defines a symbol in the current scope.
        Returns False if the symbol is already defined in THIS scope level.
        """
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str, current_scope_only: bool = False) -> Optional[Symbol]:
        """
        Looks up a symbol by name. Searches parent scopes unless current_scope_only is True.
        """
        if name in self.symbols:
            return self.symbols[name]
        if not current_scope_only and self.parent is not None:
            return self.parent.lookup(name, current_scope_only=False)
        return None

    def mark_initialized(self, name: str) -> bool:
        """Marks a symbol as initialized in the innermost scope where it is found."""
        sym = self.lookup(name)
        if sym:
            sym.is_initialized = True
            return True
        return False


class SymbolTable:
    """
    Manages the active hierarchy of Scopes during semantic analysis and execution.
    """

    def __init__(self):
        self.global_scope = Scope(name="global", level=0, parent=None)
        self.current_scope = self.global_scope
        self.all_scopes: List[Scope] = [self.global_scope]
        self._scope_counter = 0

    def enter_scope(self, name: Optional[str] = None) -> Scope:
        """Creates and enters a new child scope."""
        self._scope_counter += 1
        scope_name = name if name else f"block_{self._scope_counter}"
        new_scope = Scope(name=scope_name, level=self.current_scope.level + 1, parent=self.current_scope)
        self.current_scope.children.append(new_scope)
        self.all_scopes.append(new_scope)
        self.current_scope = new_scope
        return new_scope

    def exit_scope(self) -> Scope:
        """Exits the current scope and returns to its parent."""
        if self.current_scope.parent is not None:
            self.current_scope = self.current_scope.parent
        return self.current_scope

    def define(self, name: str, type_name: str, line: int, column: int, is_initialized: bool = False, extra: Optional[Dict[str, Any]] = None) -> Optional[Symbol]:
        """
        Defines a symbol in the current scope.
        Returns the Symbol if successful, or None if already defined in current scope.
        """
        symbol = Symbol(
            name=name,
            type_name=type_name,
            scope_level=self.current_scope.level,
            line=line,
            column=column,
            is_initialized=is_initialized,
            extra=extra
        )
        if self.current_scope.define(symbol):
            return symbol
        return None

    def lookup(self, name: str, current_scope_only: bool = False) -> Optional[Symbol]:
        """Looks up a symbol in the current scope hierarchy."""
        return self.current_scope.lookup(name, current_scope_only)

    def mark_initialized(self, name: str) -> bool:
        """Marks a symbol as initialized."""
        return self.current_scope.mark_initialized(name)

    def get_all_symbols(self) -> List[Symbol]:
        """Returns a flat list of all symbols across all scopes."""
        result: List[Symbol] = []
        for s in self.all_scopes:
            result.extend(s.symbols.values())
        return result

    def format_table(self) -> str:
        """Formats the symbol table into a clean ASCII table."""
        all_syms = self.get_all_symbols()
        if not all_syms:
            return "Symbol Table: (empty)"

        header = f"{'SCOPE (LVL)':<16} | {'IDENTIFIER':<16} | {'TYPE':<10} | {'INITIALIZED':<12} | {'DECLARED AT'}"
        sep = "=" * len(header)
        lines = [sep, header, sep]

        for s in all_syms:
            init_str = "Yes" if s.is_initialized else "No"
            loc_str = f"Line {s.line}, Col {s.column}"
            lines.append(f"{s.scope_level:<16} | {s.name:<16} | {s.type_name:<10} | {init_str:<12} | {loc_str}")

        lines.append(sep)
        return "\n".join(lines)
