"""
test_runner.py
==============
Automated Test Suite Runner for the EduScript Compiler & Interpreter.
Runs valid programs, custom keyword programs, syntax error cases,
semantic error cases, lexical error cases, and runtime error cases.
"""

import sys
import subprocess
from pathlib import Path
from typing import NamedTuple, List, Optional


class TestCase(NamedTuple):
    name: str
    file_path: str
    expected_exit_code: int
    expected_output_substrings: List[str]
    description: str


TEST_SUITE: List[TestCase] = [
    TestCase(
        name="1. Custom Hindi Keywords (example.custom)",
        file_path="example.custom",
        expected_exit_code=0,
        expected_output_substrings=["High score achieved!"],
        description="Validates purnaank, dashamlav, jabtak (while), agar/warna (if/else), dikhao (print), wapas (return)."
    ),
    TestCase(
        name="2. Hindi Keywords Factorial (tests/test_custom_hindi.custom)",
        file_path="tests/test_custom_hindi.custom",
        expected_exit_code=0,
        expected_output_substrings=["Factorial result:", "720", "Factorial verification passed!"],
        description="Validates while loop accumulator and integer comparisons in Hindi keywords."
    ),
    TestCase(
        name="3. Arithmetic & Precedence (tests/test_arithmetic.edu)",
        file_path="tests/test_arithmetic.edu",
        expected_exit_code=0,
        expected_output_substrings=["Addition:", "13", "Multiplication:", "30", "Modulo:", "1", "14", "26", "46"],
        description="Validates +, -, *, /, %, precedence climbing, parentheses, and compound assignments (+=, -=, *=, /=)."
    ),
    TestCase(
        name="4. Control Flow & Logic (tests/test_control_flow.edu)",
        file_path="tests/test_control_flow.edu",
        expected_exit_code=0,
        expected_output_substrings=["Sum of evens 1..10 (expected 30):", "30", "Sum of odds 1..10 (expected 25):", "25", "Logical AND condition passed!"],
        description="Validates while loop, if/else branch selection, modulo, and logical operators (&&, ||)."
    ),
    TestCase(
        name="5. For Loop (tests/test_for_loop.edu)",
        file_path="tests/test_for_loop.edu",
        expected_exit_code=0,
        expected_output_substrings=["Sum of squares 1..5 (expected 55):", "55"],
        description="Validates for loop initialization, condition, increment, and loop body execution."
    ),
    TestCase(
        name="6. String Operations (tests/test_strings.edu)",
        file_path="tests/test_strings.edu",
        expected_exit_code=0,
        expected_output_substrings=["Hello, Welcome to EduScript Compiler!", "String equality verified."],
        description="Validates string declaration, concatenation with +, and string equality checking."
    ),
    TestCase(
        name="7. Semantic Error: Type Mismatch (tests/error_type_mismatch.edu)",
        file_path="tests/error_type_mismatch.edu",
        expected_exit_code=3,
        expected_output_substrings=["SEMANTIC ERRORS ENCOUNTERED", "Type mismatch"],
        description="Ensures semantic analyzer catches assigning a string to an integer variable."
    ),
    TestCase(
        name="8. Semantic Error: Undeclared Variable (tests/error_undeclared_var.edu)",
        file_path="tests/error_undeclared_var.edu",
        expected_exit_code=3,
        expected_output_substrings=["SEMANTIC ERRORS ENCOUNTERED", "Undeclared variable 'b'"],
        description="Ensures semantic analyzer flags assignments to undeclared variables."
    ),
    TestCase(
        name="9. Semantic Error: Duplicate Declaration (tests/error_duplicate_decl.edu)",
        file_path="tests/error_duplicate_decl.edu",
        expected_exit_code=3,
        expected_output_substrings=["SEMANTIC ERRORS ENCOUNTERED", "Duplicate declaration of variable 'x'"],
        description="Ensures redeclaring a variable in the same scope produces a semantic error."
    ),
    TestCase(
        name="10. Syntax Error: Malformed Expression (tests/error_syntax.edu)",
        file_path="tests/error_syntax.edu",
        expected_exit_code=2,
        expected_output_substrings=["SYNTAX ERRORS ENCOUNTERED"],
        description="Ensures parser detects missing parentheses or delimiters and reports exact location."
    ),
    TestCase(
        name="11. Lexical Error: Unsupported Characters (tests/error_lexical.edu)",
        file_path="tests/error_lexical.edu",
        expected_exit_code=1,
        expected_output_substrings=["LEXICAL ERRORS ENCOUNTERED", "Unsupported character"],
        description="Ensures lexer catches invalid characters outside string literals."
    ),
    TestCase(
        name="12. Runtime Error: Division by Zero (tests/error_division_by_zero.edu)",
        file_path="tests/error_division_by_zero.edu",
        expected_exit_code=4,
        expected_output_substrings=["Runtime Error: Division by zero"],
        description="Ensures execution engine halts gracefully with runtime diagnostics on divide-by-zero."
    ),
]


def run_test(test: TestCase, base_dir: Path) -> bool:
    print("-" * 78)
    print(f"RUNNING: {test.name}")
    print(f"Desc   : {test.description}")
    print(f"File   : {test.file_path}")

    target = str(base_dir / test.file_path)
    cmd = [sys.executable, str(base_dir / "main.py"), target]

    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(base_dir))

    code_match = (res.returncode == test.expected_exit_code)
    output_combined = res.stdout + "\n" + res.stderr

    missing_substrings = [s for s in test.expected_output_substrings if s not in output_combined]
    substrings_match = len(missing_substrings) == 0

    if code_match and substrings_match:
        print(f"STATUS : PASSED (Exit Code: {res.returncode} as expected)")
        return True
    else:
        print(f"STATUS : FAILED")
        if not code_match:
            print(f"  * Expected exit code {test.expected_exit_code}, got {res.returncode}")
        if not substrings_match:
            print(f"  * Missing expected output substrings: {missing_substrings}")
        print("\n--- Process STDOUT ---")
        print(res.stdout)
        print("--- Process STDERR ---")
        print(res.stderr)
        return False


def main():
    base_dir = Path(__file__).parent.resolve()
    print("\n" + "=" * 78)
    print("       EDUSCRIPT COMPILER DESIGN - AUTOMATED TEST SUITE RUNNER")
    print("=" * 78)
    print(f"Total Test Cases: {len(TEST_SUITE)}\n")

    passed = 0
    failed = 0

    for test in TEST_SUITE:
        if run_test(test, base_dir):
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 78)
    print("                         TEST SUITE SUMMARY")
    print("=" * 78)
    print(f"Total Tests : {len(TEST_SUITE)}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {failed}")
    print(f"Success Rate: {(passed / len(TEST_SUITE)) * 100:.1f}%")
    print("=" * 78 + "\n")

    if failed > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED SUCCESSFULLY!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
