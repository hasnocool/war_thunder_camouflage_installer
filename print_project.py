import os
import subprocess
import pyperclip
import argparse

# List of directories and files to exclude
EXCLUDE_PATTERNS = [
    "target", "cache", "notes", "binaries", ".idea", ".vscode", ".git",
    "Cargo.lock", "clippy_combined_output.txt", "clippy_combined_output.txt_final.txt",
    "clippy_full_files_output.txt", "config.ini", "../wtci_db/war_thunder_camouflages.db",
    "*.db", "build_script_v1.py",
    # New patterns added
    "build_script.py", "Cargo.toml", "CHANGE.log", "check.py", "print_project.py",
    "README.md", "TAGS.json", "TODO.md", "TREE.md",
    "avatar.jpg", "banner.png", "logo.png", "preview.png"
]

EXCLUDE_EXTENSIONS = [".rs.bk", ".db"]

def should_exclude(file_path):
    """Check if a file or directory should be excluded based on the given patterns."""
    base_name = os.path.basename(file_path)
    # Ignore hidden files and directories (starting with a dot)
    if base_name.startswith('.'):
        return True
    # Check for patterns in the blacklist
    for pattern in EXCLUDE_PATTERNS:
        if pattern in file_path:
            return True
    # Check for excluded extensions
    for ext in EXCLUDE_EXTENSIONS:
        if file_path.endswith(ext):
            return True
    return False

def list_files_recursively(base_dir):
    """Recursively list all files in the base directory, excluding specified patterns."""
    file_list = []
    for root, dirs, files in os.walk(base_dir):
        # Exclude specified directories and hidden directories
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
        for file in files:
            # Exclude specified files and hidden files
            file_path = os.path.join(root, file)
            if not should_exclude(file_path):
                file_list.append(file_path)
    return file_list

def generate_file_tree(base_dir):
    """Generate a directory and file tree structure."""
    tree = ""
    for root, dirs, files in os.walk(base_dir):
        # Exclude specified directories and hidden directories
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
        level = root.replace(base_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        tree += f"{indent}{os.path.basename(root)}/\n"
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            file_path = os.path.join(root, f)
            if not should_exclude(file_path):
                tree += f"{subindent}{f}\n"
    return tree

def print_file_contents(file_path):
    """Return the contents of a file with a divider."""
    divider = f"\n{'=' * 40}\n{file_path}\n{'=' * 40}\n"
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return divider + file.read()
    except Exception as e:
        return divider + f"Error reading file: {e}"

def capture_error_output(command):
    """Capture both stdout and stderr from a command execution."""
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        return result.stdout, result.stderr
    except Exception as e:
        return "", f"Error executing command '{command}': {e}"

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

def format_llm_prompt(user_query, file_context, error_output, file_tree):
    """Format the LLM prompt in a structured format."""
    prompt = (
        "SYSTEM: YOU ARE A RUST PROGRAMMING EXPERT.\n"
        "USER: HERE IS THE CONTEXT OF MY RUST PROJECT. PLEASE ANALYZE THE CODE AND ERROR OUTPUT TO PROVIDE A DETAILED RESPONSE.\n\n"
        f"FILE TREE STRUCTURE:\n{file_tree}\n"
        f"FILES CONTENT:\n{file_context}\n"
        f"ERROR OUTPUT:\n{error_output}\n"
        "QUERY:\n"
        f"{user_query.upper()}\n"
        "AI: PLEASE PROVIDE A DETAILED AND ACTIONABLE RESPONSE TO THE QUERY ABOVE, EXPLAINING THE CONTEXT, ROOT CAUSE, AND STEPS NEEDED TO RESOLVE OR IMPROVE IT."
    )
    return prompt

def ollama_query(query):
    """Send a query to the Ollama model and return the response."""
    try:
        result = subprocess.run(
            ["ollama", "query", query],
            capture_output=True,
            text=True,
            shell=True
        )
        return result.stdout
    except Exception as e:
        return f"Error running Ollama query: {e}"

def main():
    # Parse command-line arguments
    args = parse_arguments()

    # Define the base directory (current working directory)
    base_dir = os.getcwd()

    # Generate the file tree
    file_tree = generate_file_tree(base_dir)

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

    # Collect file context for LLM
    file_context = ""
    for file in selected_files:
        file_content = print_file_contents(file)
        output += file_content
        file_context += file_content

    # Include cargo build or clippy errors if specified
    error_output = ""
    if args.build:
        stdout, stderr = capture_error_output("cargo build")
        output += "\n" + "=" * 40 + "\nCargo Build Output\n" + "=" * 40 + "\n"
        output += stdout
        error_output = stderr
        output += "\n" + "=" * 40 + "\nCargo Build Errors\n" + "=" * 40 + "\n"
        output += stderr

    # Include the user's query for ChatGPT if specified
    if args.query:
        formatted_prompt = format_llm_prompt(args.query, file_context, error_output, file_tree)
        output += "\n" + "=" * 40 + "\nQuery for ChatGPT\n" + "=" * 40 + "\n"
        output += formatted_prompt
        # Include Ollama response if specified
        output += "\n" + "=" * 40 + "\nOllama Response\n" + "=" * 40 + "\n"
        output += ollama_query(args.query)

    # Print and copy the output to the clipboard
    print(output)
    pyperclip.copy(output)

if __name__ == "__main__":
    main()
