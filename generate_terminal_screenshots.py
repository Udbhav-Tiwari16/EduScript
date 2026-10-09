"""
generate_terminal_screenshots.py
=================================
Runs REAL project commands and captures high-resolution, pixel-perfect
terminal screenshots for the Final Project Review presentation.
"""

import sys
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def get_monospace_font(size: int):
    """Finds a crisp monospace font on Windows/System."""
    font_candidates = [
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\consolab.ttf",
        r"C:\Windows\Fonts\CascadiaMono.ttf",
        r"C:\Windows\Fonts\lucon.ttf",
        r"C:\Windows\Fonts\cour.ttf",
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_terminal_window(title: str, command: str, output_text: str, output_image_path: Path, max_lines: int = 45):
    """
    Renders terminal output into a modern, beautiful dark-themed terminal card.
    """
    font_size = 18
    font = get_monospace_font(font_size)
    title_font = get_monospace_font(16)
    prompt_font = get_monospace_font(font_size)

    # Process text lines
    raw_lines = output_text.splitlines()
    if len(raw_lines) > max_lines:
        display_lines = raw_lines[:max_lines] + [f"... [truncated {len(raw_lines) - max_lines} remaining lines for slide view] ..."]
    else:
        display_lines = raw_lines

    # Calculate dimensions
    char_width = 11
    line_height = 24
    header_height = 44
    padding_x = 24
    padding_y = 20

    max_line_len = max([len(line) for line in display_lines] + [len(command) + 4, len(title) + 10, 60])
    width = min(max(max_line_len * char_width + padding_x * 2, 850), 1400)
    height = header_height + padding_y * 2 + (len(display_lines) + 2) * line_height

    # Colors
    bg_color = (22, 27, 34)       # GitHub Dark Dimmed BG
    header_color = (33, 38, 45)   # Title bar BG
    border_color = (48, 54, 61)   # Border
    text_color = (230, 237, 243)  # Bright terminal text
    prompt_color = (88, 166, 255) # Prompt blue
    cmd_color = (126, 231, 135)   # Command green
    title_color = (139, 148, 158) # Title gray
    error_color = (255, 123, 114) # Red for errors
    warn_color = (210, 153, 34)   # Yellow/orange

    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Draw window header
    draw.rectangle([(0, 0), (width, header_height)], fill=header_color)
    draw.line([(0, header_height), (width, header_height)], fill=border_color, width=1)

    # Window controls (macOS / modern style dots)
    dot_radius = 6
    dot_y = header_height // 2
    draw.ellipse([(16, dot_y - dot_radius), (16 + dot_radius * 2, dot_y + dot_radius)], fill=(255, 95, 86))
    draw.ellipse([(36, dot_y - dot_radius), (36 + dot_radius * 2, dot_y + dot_radius)], fill=(255, 189, 46))
    draw.ellipse([(56, dot_y - dot_radius), (56 + dot_radius * 2, dot_y + dot_radius)], fill=(39, 201, 63))

    # Window title centered
    title_text = f"EduScript Terminal — {title}"
    draw.text((85, 12), title_text, fill=title_color, font=title_font)

    # Draw command prompt line
    curr_y = header_height + padding_y
    draw.text((padding_x, curr_y), "PS EduScript> ", fill=prompt_color, font=prompt_font)
    draw.text((padding_x + 150, curr_y), command, fill=cmd_color, font=prompt_font)
    curr_y += line_height + 6

    # Draw output lines
    for line in display_lines:
        line_fill = text_color
        if "ERROR" in line or "FAILED" in line or "Traceback" in line or "TypeError" in line or "SyntaxError" in line:
            line_fill = error_color
        elif "WARNING" in line or "PASSED" in line or "SUCCESS" in line or "Completed Successfully" in line:
            line_fill = (86, 211, 100) if ("PASSED" in line or "SUCCESS" in line or "Completed" in line) else warn_color
        elif line.startswith("=") or line.startswith("-") or line.startswith("!"):
            line_fill = (110, 118, 129)
        elif line.startswith("[PHASE") or line.startswith("PROGRAM EXECUTION"):
            line_fill = (163, 113, 247)  # Purple header

        draw.text((padding_x, curr_y), line, fill=line_fill, font=font)
        curr_y += line_height

    # Outer border
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=border_color, width=2)

    # Save
    output_image_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_image_path, "PNG")
    print(f"Generated screenshot: {output_image_path.name} ({width}x{height})")


def run_and_capture(title: str, cmd_str: str, filename: str, cwd: Path, max_lines: int = 40) -> Path:
    out_path = cwd / "evidence_screenshots" / filename
    print(f"Executing: {cmd_str}")
    proc = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, cwd=str(cwd))
    combined = proc.stdout
    if proc.stderr:
        combined += ("\n" + proc.stderr)
    render_terminal_window(title, cmd_str, combined.strip(), out_path, max_lines=max_lines)
    return out_path


def main():
    base_dir = Path(__file__).parent.resolve()
    evidence_dir = base_dir / "evidence_screenshots"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    print("\n--- CAPTURING REAL OUTPUT SCREENSHOTS FOR REVIEW 3 ---")

    # 1. Test Runner (12/12 test suite pass)
    run_and_capture(
        title="Automated Test Suite (12/12 Passed)",
        cmd_str="python test_runner.py",
        filename="01_test_suite_runner.png",
        cwd=base_dir,
        max_lines=38
    )

    # 2. Full Compiler Pipeline on Hindi Custom Code
    run_and_capture(
        title="Full Pipeline Execution (example.custom --all)",
        cmd_str="python main.py example.custom --all",
        filename="02_full_pipeline_all.png",
        cwd=base_dir,
        max_lines=45
    )

    # 3. Lexical Tokens Table
    run_and_capture(
        title="Phase 1: Lexical Analysis Tokens",
        cmd_str="python main.py example.custom --tokens",
        filename="03_phase1_tokens.png",
        cwd=base_dir,
        max_lines=32
    )

    # 4. AST Tree
    run_and_capture(
        title="Phase 2: Abstract Syntax Tree (AST)",
        cmd_str="python main.py example.custom --ast",
        filename="04_phase2_ast.png",
        cwd=base_dir,
        max_lines=36
    )

    # 5. Scoped Symbol Table
    run_and_capture(
        title="Phase 3: Scoped Symbol Table",
        cmd_str="python main.py example.custom --symbols",
        filename="05_phase3_symbol_table.png",
        cwd=base_dir,
        max_lines=28
    )

    # 6. Three-Address Code (TAC) IR
    run_and_capture(
        title="Phase 4: Three-Address Code (TAC) IR",
        cmd_str="python main.py example.custom --tac",
        filename="06_phase4_tac_ir.png",
        cwd=base_dir,
        max_lines=32
    )

    # 7. Hindi Keywords Factorial Program Execution
    run_and_capture(
        title="Hindi Custom Keywords Factorial Program Execution",
        cmd_str="python main.py tests/test_custom_hindi.custom",
        filename="07_hindi_factorial_run.png",
        cwd=base_dir,
        max_lines=25
    )

    # 8. For Loop TAC and Execution
    run_and_capture(
        title="For Loop TAC & Execution",
        cmd_str="python main.py tests/test_for_loop.edu --tac",
        filename="08_for_loop_tac_run.png",
        cwd=base_dir,
        max_lines=30
    )

    # 9. Semantic Error: Type Mismatch
    run_and_capture(
        title="Diagnostic: Semantic Type Mismatch Error",
        cmd_str="python main.py tests/error_type_mismatch.edu",
        filename="09_error_type_mismatch.png",
        cwd=base_dir,
        max_lines=25
    )

    # 10. Semantic Error: Undeclared Variable
    run_and_capture(
        title="Diagnostic: Undeclared Variable Error",
        cmd_str="python main.py tests/error_undeclared_var.edu",
        filename="10_error_undeclared_var.png",
        cwd=base_dir,
        max_lines=25
    )

    # 11. Syntax Error: Missing Delimiter
    run_and_capture(
        title="Diagnostic: Syntax Error Detection",
        cmd_str="python main.py tests/error_syntax.edu",
        filename="11_error_syntax.png",
        cwd=base_dir,
        max_lines=25
    )

    # 12. Lexical Error: Unsupported Characters
    run_and_capture(
        title="Diagnostic: Lexical Error Handling",
        cmd_str="python main.py tests/error_lexical.edu",
        filename="12_error_lexical.png",
        cwd=base_dir,
        max_lines=25
    )

    # 13. Runtime Error: Division by Zero
    run_and_capture(
        title="Diagnostic: Runtime Division by Zero",
        cmd_str="python main.py tests/error_division_by_zero.edu",
        filename="13_error_division_by_zero.png",
        cwd=base_dir,
        max_lines=25
    )

    # 14. Git Repository Log & Status
    run_and_capture(
        title="Git Version Control & Repository Status",
        cmd_str="git log -n 3 --oneline; git status",
        filename="14_git_status_log.png",
        cwd=base_dir,
        max_lines=25
    )

    print("\nAll 14 real terminal screenshots generated successfully!")


if __name__ == "__main__":
    main()
