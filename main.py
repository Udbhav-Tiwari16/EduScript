"""
main.py
=======
Executable entry point for the customizable Python compiler's Lexical Analysis stage.

Usage:
    python main.py
    python main.py <source_file_path>
    python main.py <source_file_path> --config <custom_config.json>

Steps executed:
1. Load configuration from config.json (or specified config path).
2. Load keyword mappings from keyword_mapping.json.
3. Load token definitions from default_tokens.json.
4. Read the target source code file.
5. Execute the Lexer.
6. Display a formatted token breakdown highlighting custom keywords and canonical meanings.
7. Report lexical errors clearly with line and column positions.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

from lexer import Lexer, Token, LexicalError


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Loads and parses a JSON file with error handling."""
    if not file_path.exists():
        print(f"[Error] Required file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[Error] Failed to parse JSON file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def resolve_path(base_dir: Path, target_path_str: str) -> Path:
    """Resolves relative paths with respect to base_dir."""
    p = Path(target_path_str)
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def print_token_table(tokens: list[Token]):
    """Prints the list of tokens in a formatted table."""
    print("=" * 78)
    print(f"{'LINE:COL':<10} | {'TOKEN TYPE':<12} | {'LEXEME':<22} | {'CANONICAL MEANING'}")
    print("=" * 78)

    for token in tokens:
        canon_display = f"canonical: {token.canonical}" if token.canonical else "-"
        pos = f"{token.line}:{token.column}"
        # Truncate lexeme for neat table display if very long, but show full for normal
        lexeme_disp = token.lexeme if len(token.lexeme) <= 22 else token.lexeme[:19] + "..."
        print(f"{pos:<10} | {token.type:<12} | {lexeme_disp:<22} | {canon_display}")

    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(
        description="Run lexical analysis on custom source code with customizable keywords."
    )
    parser.add_argument(
        "source_file",
        nargs="?",
        default=None,
        help="Optional path to custom source file (overrides config.json source_file)."
    )
    parser.add_argument(
        "--config",
        "-c",
        default="config.json",
        help="Path to configuration JSON file (default: config.json)."
    )

    args = parser.parse_args()

    # Determine base directory from config file location
    config_path = Path(args.config).resolve()
    base_dir = config_path.parent

    # 1. Load configuration
    config = load_json_file(config_path)

    # 2. Resolve configured paths
    mapping_path = resolve_path(base_dir, config.get("keyword_mapping_file", "keyword_mapping.json"))
    tokens_path = resolve_path(base_dir, config.get("default_tokens_file", "default_tokens.json"))
    
    # Allow command-line source file argument to override config
    if args.source_file:
        source_path = Path(args.source_file).resolve()
    else:
        source_path = resolve_path(base_dir, config.get("source_file", "example.custom"))

    # 3. Load keyword mapping and default tokens
    keyword_mapping = load_json_file(mapping_path)
    default_tokens = load_json_file(tokens_path)
    lexer_settings = config.get("lexer_settings", {})

    print("\n" + "=" * 78)
    print("        CUSTOMIZABLE COMPILER - LEXICAL ANALYSIS STAGE (PHASE 1)")
    print("=" * 78)
    print(f"Config File       : {config_path.name}")
    print(f"Source Code File  : {source_path}")
    print(f"Keyword Mappings  : {len(keyword_mapping)} mapped entries")
    print(f"Operators Defined : {len(default_tokens.get('operators', []))} operators")
    print(f"Delimiters Defined: {len(default_tokens.get('delimiters', []))} delimiters")
    print("=" * 78 + "\n")

    # 4. Read source code
    if not source_path.exists():
        print(f"[Error] Source file not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(source_path, "r", encoding="utf-8") as f:
            source_code = f.read()
    except Exception as e:
        print(f"[Error] Could not read source file {source_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Initialize Lexer and Tokenize
    lexer = Lexer(
        keyword_mapping=keyword_mapping,
        token_definitions=default_tokens,
        settings=lexer_settings
    )

    tokens, errors = lexer.tokenize(source_code)

    # 6. Display Token Stream
    print(f"--- TOKEN STREAM ({len(tokens)} tokens generated) ---")
    print_token_table(tokens)

    # 7. Print summary breakdown by token type
    type_counts: Dict[str, int] = {}
    for tok in tokens:
        type_counts[tok.type] = type_counts.get(tok.type, 0) + 1

    counts_str = ", ".join(f"{k}: {v}" for k, v in sorted(type_counts.items()))
    print(f"\nToken Breakdown: {counts_str}")

    # 8. Report lexical errors
    if errors:
        print("\n" + "!" * 78)
        print(f"LEXICAL ERRORS ENCOUNTERED: {len(errors)}")
        print("!" * 78)
        for err in errors:
            print(f"  * {err}")
        print("!" * 78)
        print(f"\nLexical Analysis Finished with {len(errors)} error(s).\n")
        sys.exit(1)
    else:
        print("\nLexical Analysis Completed Successfully (0 errors).\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
