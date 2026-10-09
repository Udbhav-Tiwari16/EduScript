"""
generate_clean_terminal_evidence.py
===================================
Runs REAL EduScript commands and renders ONLY the clean terminal content area
(starting directly at the prompt 'PS EduScript> <command>' through the output).
Contains NO window title bars, NO window buttons (dots), and NO fake frames.
"""

import sys
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def get_monospace_font(size: int):
    """Finds a crisp monospace font on Windows."""
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


def render_clean_terminal(command: str, output_text: str, output_image_path: Path, max_lines: int = 45):
    """
    Renders pure terminal content without title bar, frame, or window buttons.
    Starts directly with the command prompt line.
    """
    font_size = 18
    font = get_monospace_font(font_size)
    prompt_font = get_monospace_font(font_size)

    # Process text lines
    raw_lines = output_text.splitlines()
    if len(raw_lines) > max_lines:
        display_lines = raw_lines[:max_lines] + [f"... [truncated {len(raw_lines) - max_lines} remaining lines] ..."]
    else:
        display_lines = raw_lines

    # Calculate dimensions
    char_width = 11
    line_height = 24
    padding_x = 18
    padding_y = 16

    max_line_len = max([len(line) for line in display_lines] + [len(command) + 16, 55])
    width = min(max(max_line_len * char_width + padding_x * 2, 800), 1350)
    height = padding_y * 2 + (len(display_lines) + 1) * line_height

    # Modern Dark Terminal Color Scheme (Clean VS Code / Windows Terminal dark)
    bg_color = (24, 24, 24)        # Deep neutral terminal dark
    text_color = (220, 220, 220)   # Clean terminal text
    prompt_color = (78, 201, 176)  # PowerShell cyan/teal prompt
    cmd_color = (206, 145, 120)    # Command highlight
    error_color = (244, 71, 71)    # Red for errors
    success_color = (106, 153, 85) # Green for success
    header_color = (86, 156, 214)  # Blue for phase markers
    border_color = (45, 45, 48)    # Subtle inner border

    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Draw command prompt line (starts immediately at top padding)
    curr_y = padding_y
    draw.text((padding_x, curr_y), "PS EduScript> ", fill=prompt_color, font=prompt_font)
    draw.text((padding_x + 145, curr_y), command, fill=cmd_color, font=prompt_font)
    curr_y += line_height + 4

    # Draw output lines
    for line in display_lines:
        line_fill = text_color
        if "ERROR" in line or "FAILED" in line or "Traceback" in line or "TypeError" in line or "SyntaxError" in line:
            line_fill = error_color
        elif "WARNING" in line or "PASSED" in line or "SUCCESS" in line or "Completed Successfully" in line:
            line_fill = success_color
        elif line.startswith("=") or line.startswith("-") or line.startswith("!"):
            line_fill = (100, 100, 100)
        elif line.startswith("[PHASE") or line.startswith("PROGRAM EXECUTION"):
            line_fill = header_color

        draw.text((padding_x, curr_y), line, fill=line_fill, font=font)
        curr_y += line_height

    # Clean thin outer boundary
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=border_color, width=1)

    # Save
    output_image_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_image_path, "PNG")
    print(f"Rendered clean cropped terminal evidence: {output_image_path.name} ({width}x{height})")


def run_and_capture(cmd_str: str, filename: str, cwd: Path, max_lines: int = 40) -> Path:
    out_path = cwd / "evidence_screenshots" / filename
    print(f"Executing: {cmd_str}")
    proc = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, cwd=str(cwd))
    combined = proc.stdout
    if proc.stderr:
        combined += ("\n" + proc.stderr)
    render_clean_terminal(cmd_str, combined.strip(), out_path, max_lines=max_lines)
    return out_path


def main():
    base_dir = Path(__file__).parent.resolve()
    evidence_dir = base_dir / "evidence_screenshots"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    print("\n--- GENERATING CLEAN CROPPED TERMINAL EVIDENCE (NO WINDOW BUTTONS / NO TITLE BAR) ---")

    # 1. Test Suite Runner
    run_and_capture(
        cmd_str="python test_runner.py",
        filename="01_test_suite_runner.png",
        cwd=base_dir,
        max_lines=38
    )

    # 2. Full Pipeline --all
    run_and_capture(
        cmd_str="python main.py example.custom --all",
        filename="02_full_pipeline_all.png",
        cwd=base_dir,
        max_lines=45
    )

    # 3. Lexical Analysis Tokens
    run_and_capture(
        cmd_str="python main.py example.custom --tokens",
        filename="03_phase1_tokens.png",
        cwd=base_dir,
        max_lines=32
    )

    # 4. AST Tree
    run_and_capture(
        cmd_str="python main.py example.custom --ast",
        filename="04_phase2_ast.png",
        cwd=base_dir,
        max_lines=36
    )

    # 5. Symbol Table
    run_and_capture(
        cmd_str="python main.py example.custom --symbols",
        filename="05_phase3_symbol_table.png",
        cwd=base_dir,
        max_lines=28
    )

    # 6. TAC IR
    run_and_capture(
        cmd_str="python main.py example.custom --tac",
        filename="06_phase4_tac_ir.png",
        cwd=base_dir,
        max_lines=32
    )

    # 7. Hindi Factorial Run
    run_and_capture(
        cmd_str="python main.py tests/test_custom_hindi.custom",
        filename="07_hindi_factorial_run.png",
        cwd=base_dir,
        max_lines=25
    )

    # 8. For Loop TAC Run
    run_and_capture(
        cmd_str="python main.py tests/test_for_loop.edu --tac",
        filename="08_for_loop_tac_run.png",
        cwd=base_dir,
        max_lines=30
    )

    # 9. Semantic Error: Type Mismatch
    run_and_capture(
        cmd_str="python main.py tests/error_type_mismatch.edu",
        filename="09_error_type_mismatch.png",
        cwd=base_dir,
        max_lines=25
    )

    # 10. Semantic Error: Undeclared Variable
    run_and_capture(
        cmd_str="python main.py tests/error_undeclared_var.edu",
        filename="10_error_undeclared_var.png",
        cwd=base_dir,
        max_lines=25
    )

    # 11. Syntax Error
    run_and_capture(
        cmd_str="python main.py tests/error_syntax.edu",
        filename="11_error_syntax.png",
        cwd=base_dir,
        max_lines=25
    )

    # 12. Lexical Error
    run_and_capture(
        cmd_str="python main.py tests/error_lexical.edu",
        filename="12_error_lexical.png",
        cwd=base_dir,
        max_lines=25
    )

    # 13. Runtime Error
    run_and_capture(
        cmd_str="python main.py tests/error_division_by_zero.edu",
        filename="13_error_division_by_zero.png",
        cwd=base_dir,
        max_lines=25
    )

    # 14. Git Status & Log
    run_and_capture(
        cmd_str="git log -n 3 --oneline; git status",
        filename="14_git_status_log.png",
        cwd=base_dir,
        max_lines=25
    )

    print("\nClean cropped terminal evidence generated successfully!")


if __name__ == "__main__":
    main()
