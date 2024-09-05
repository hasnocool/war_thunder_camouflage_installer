import os
import subprocess
import pyperclip
import argparse

# List of directories and files to exclude
EXCLUDE_PATTERNS = [
    "target", "cache", "notes", "binaries", ".idea", ".vscode",
    "Cargo.lock", "clippy_combined_output.txt", "clippy_combined_output.txt_final.txt",
    "clippy_full_files_output.txt", "config.ini", "../wtci_db/war_thunder_camouflages.db",
    "*.db", "build_script_v1.py"
]

EXCLUDE_EXTENSIONS = [".rs.bk", ".db"]

def should_exclude(file_path):
    """Check if a file or directory should be excluded based on the given patterns."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in file_path:
            return True
    for ext in EXCLUDE_EXTENSIONS:
        if file_path.endswith(ext):
            return True
    return False

def list_files_recursively(base_dir):
    """Recursively list all files in the base directory, excluding specified patterns."""
    file_list = []
    for root, dirs, files in os.walk(base_dir):
        # Exclude specified directories
        dirs[:] = [d for d in dirs if not should_exclude(d)]
        for file in files:
            # Exclude specified files
            file_path = os.path.join(root, file)
            if not should_exclude(file_path):
                file_list.append(file_path)
    return file_list

def print_file_contents(file_path):
    """Return the contents of a file with a divider."""
    divider = f"\n{'=' * 40}\n{file_path}\n{'=' * 40}\n"
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return divider + file.read()
    except Exception as e:
        return divider + f"Error reading file: {e}"

def select_files(files):
    """Allow the user to select files from a list."""
    print("Select files to print by entering their numbers separated by commas (e.g., 1,2):")
    for i, file in enumerate(files):
        print(f"{i + 1}: {file}")

    selection = input("Your selection: ").split(',')
    selected_files = []

    try:
        for index in selection:
            idx = int(index.strip()) - 1
            if 0 <= idx < len(files):
                selected_files.append(files[idx])
            else:
                print(f"Invalid selection: {index.strip()}")
    except ValueError:
        print("Invalid input. Please enter numbers separated by commas.")

    return selected_files

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Print contents of Rust project files and capture cargo build errors.")
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Print all files without selection."
    )
    parser.add_argument(
        "-f", "--files",
        nargs="*",
        help="Specific files to print by their index (e.g., 1 2 3)."
    )
    parser.add_argument(
        "-b", "--build",
        action="store_true",
        help="Include cargo build errors in the output."
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="Query for ChatGPT to ask about the project (e.g., 'How to fix the borrow checker issue?')."
    )
    return parser.parse_args()

def run_cargo_command(command):
    """Run a cargo command and capture its stderr output."""
    result = subprocess.run(command, stderr=subprocess.PIPE, text=True, shell=True)
    return result.stderr

def format_llm_prompt(user_query):
    """Format the LLM prompt in a structured format."""
    prompt = (
        "SYSTEM: YOU ARE A RUST PROGRAMMING EXPERT.\n"
        "USER: HERE IS THE CONTEXT OF MY RUST PROJECT. PLEASE ANALYZE THE CODE AND ERROR OUTPUT TO PROVIDE A DETAILED RESPONSE.\n\n"
        "FILES CONTENT:\n"
        "...\n"  # Placeholder for files content
        "ERROR OUTPUT:\n"
        "...\n"  # Placeholder for error output
        "QUERY:\n"
        f"{user_query.upper()}\n"
        "AI: PLEASE PROVIDE A DETAILED AND ACTIONABLE RESPONSE TO THE QUERY ABOVE, EXPLAINING THE CONTEXT, ROOT CAUSE, AND STEPS NEEDED TO RESOLVE OR IMPROVE IT."
    )
    return prompt

def main():
    # Parse command-line arguments
    args = parse_arguments()

    # Define the base directory (current working directory)
    base_dir = os.getcwd()

    # Get the list of files in the base directory, recursively excluding specified patterns
    all_files = list_files_recursively(base_dir)

    # Determine files to print
    if args.all:
        selected_files = all_files
    elif args.files:
        try:
            selected_files = [all_files[int(i) - 1] for i in args.files if 0 < int(i) <= len(all_files)]
        except ValueError:
            print("Invalid file indices. Please provide valid numbers.")
            return
    else:
        selected_files = select_files(all_files)

    # Collect the output in a string
    output = ""

    # Append the contents of each selected file to the output
    for file in selected_files:
        output += print_file_contents(file)

    # Include cargo build or clippy errors if specified
    if args.build:
        output += "\n" + "=" * 40 + "\nCargo Build Errors\n" + "=" * 40 + "\n"
        output += run_cargo_command("cargo build")

    # Include the user's query for ChatGPT if specified
    if args.query:
        formatted_prompt = format_llm_prompt(args.query)
        output += "\n" + "=" * 40 + "\nQuery for ChatGPT\n" + "=" * 40 + "\n"
        output += formatted_prompt

    # Print and copy the output to the clipboard
    print(output)
    pyperclip.copy(output)

if __name__ == "__main__":
    main()
