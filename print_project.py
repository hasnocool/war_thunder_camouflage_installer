import os
import pyperclip

def list_files_in_directory(directory, extensions):
    """List all files in the given directory with the specified extensions."""
    file_list = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_list.append(os.path.join(root, file))
    return file_list

def print_file_contents(file_path):
    """Return the contents of a file with a divider."""
    divider = f"\n{'=' * 40}\n{file_path}\n{'=' * 40}\n"
    with open(file_path, 'r', encoding='utf-8') as file:
        return divider + file.read()

def main():
    # Define the extensions and directories
    rust_extensions = ['.rs']
    current_dir = os.getcwd()
    src_dir = os.path.join(current_dir, 'src')
    cargo_toml = os.path.join(current_dir, 'Cargo.toml')

    # Get the list of Rust files in the src directory
    rust_files = list_files_in_directory(src_dir, rust_extensions)

    # Collect the output in a string
    output = ""

    # Append the contents of each Rust file to the output
    for rust_file in rust_files:
        output += print_file_contents(rust_file)

    # Append the contents of Cargo.toml if it exists
    if os.path.isfile(cargo_toml):
        output += print_file_contents(cargo_toml)
    else:
        output += f"\n{'=' * 40}\nCargo.toml not found in the current directory.\n{'=' * 40}\n"

    # Print and copy the output to the clipboard
    print(output)
    pyperclip.copy(output)

if __name__ == "__main__":
    main()



