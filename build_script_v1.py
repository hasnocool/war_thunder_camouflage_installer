import os
import subprocess
import sys
import requests
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_API_URL = "http://192.168.1.223:11434"
OLLAMA_MODEL = "llama3.1"

def run_command(command):
    """Run a command and return its output and error (if any)."""
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def increment_version(version):
    """Increment the version number."""
    parts = version.split('.')
    if len(parts) >= 3:
        parts[2] = str(int(parts[2].split('-')[0]) + 1)
    return '.'.join(parts)

def check_repo_status():
    """Check if there are uncommitted changes."""
    _, _, return_code = run_command('git diff-index --quiet HEAD --')
    return return_code == 0

def generate_commit_message_with_ollama(changes_summary):
    """Generate a commit message using Ollama LLM."""
    prompt = (
        "You are an AI assistant that helps generate concise and informative commit messages "
        "for a software repository. The repository is a Rust project that is being maintained "
        "by multiple developers. Please read the following summary of changes and generate a "
        "commit message that is clear, concise, and follows the conventional commit style. "
        "The commit message should start with a capitalized verb in the imperative mood and "
        "should not exceed 50 characters in the subject line.\n\n"
        f"Changes Summary:\n{changes_summary}\n\n"
        "Expected Output:\n- A single-line commit subject.\n- An optional commit body with a "
        "brief description of the changes, if necessary."
    )
    
    response = requests.post(
        f"{OLLAMA_API_URL}/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt}
    )
    
    if response.status_code == 200:
        return response.json().get('text', '').strip()
    else:
        logger.error("Failed to get response from Ollama API: %s", response.text)
        return None

def handle_large_file_error(error_message):
    """Handle the case where a large file is detected in the repository."""
    large_file_match = re.search(r"File (.*?) is .*?MB", error_message)
    if large_file_match:
        large_file = large_file_match.group(1)
        print(f"\nError: Large file detected: {large_file}")
        print("This file exceeds GitHub's file size limit of 100.00 MB.")
        print("\nTo resolve this issue, follow these steps:")
        print(f"1. Remove the large file from Git history:")
        print(f"   git filter-branch --force --index-filter \"git rm --cached --ignore-unmatch {large_file}\" --prune-empty --tag-name-filter cat -- --all")
        print("2. Force push the changes:")
        print("   git push origin --force --all")
        print("3. Force push the tags:")
        print("   git push origin --force --tags")
        print("\nAfter completing these steps, run this script again.")
    else:
        print("\nAn error occurred while pushing to the repository.")
        print("Error message:", error_message)

def stage_and_commit_changes():
    """Stage all changes and commit them using a generated commit message."""
    # Stage all changes
    run_command('git add .')

    # Get a summary of changes
    changes_summary, _, _ = run_command('git diff --cached --name-status')
    
    if not changes_summary:
        print("No changes to commit.")
        return False

    # Generate commit message using Ollama
    commit_message = generate_commit_message_with_ollama(changes_summary)

    if not commit_message:
        print("Failed to generate commit message. Using default message.")
        commit_message = "Update repository"

    # Commit changes
    _, error, return_code = run_command(f'git commit -m "{commit_message}"')
    
    if return_code != 0:
        print(f"Error committing changes: {error}")
        return False

    print("Changes committed successfully.")
    return True

def update_cargo_toml(new_version):
    """Update the version in Cargo.toml without changing formatting."""
    with open('Cargo.toml', 'r') as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if line.startswith('version = '):
            lines[i] = f'version = "{new_version}"\n'
            break

    with open('Cargo.toml', 'w') as file:
        file.writelines(lines)

def main():
    # Check if we're in a git repository
    if not os.path.isdir('.git'):
        print("Error: This script must be run from the root of a git repository.")
        return

    # Stage and commit changes if there are any
    if not check_repo_status():
        print("Uncommitted changes detected. Staging and committing changes...")
        if not stage_and_commit_changes():
            print("Failed to commit changes. Please commit manually and run the script again.")
            return

    # Get the latest tag
    latest_tag, error, _ = run_command('git describe --tags --abbrev=0')

    if error and "No names found" in error:
        print("No existing tags found. Creating initial tag v1.0.0-beta")
        new_tag = "v1.0.0-beta"
    elif latest_tag:
        print(f"Latest tag: {latest_tag}")
        version = latest_tag[1:] if latest_tag.startswith('v') else latest_tag
        new_version = increment_version(version)
        new_tag = f"v{new_version}-beta"
    else:
        print(f"Error fetching latest tag: {error}")
        return

    # Update Cargo.toml with the new version
    update_cargo_toml(new_tag[1:])  # Remove 'v' prefix
    
    # Commit the Cargo.toml change
    run_command('git add Cargo.toml')
    run_command(f'git commit -m "Update version to {new_tag} in Cargo.toml"')

    print(f"Creating new tag: {new_tag}")

    # Create the new tag
    _, error, _ = run_command(f'git tag {new_tag}')
    if error:
        print(f"Error creating tag: {error}")
        return

    # Try to push the new tag and changes
    _, error, return_code = run_command('git push origin master')
    if return_code != 0:
        handle_large_file_error(error)
        run_command(f'git tag -d {new_tag}')
        return

    _, error, return_code = run_command(f'git push origin {new_tag}')
    if return_code != 0:
        handle_large_file_error(error)
        run_command(f'git tag -d {new_tag}')
        return

    print(f"Tag {new_tag} created and pushed to remote.")

    # Generate release notes using Ollama
    changes_summary, _, _ = run_command('git log -1 --pretty=%B')
    release_notes = generate_commit_message_with_ollama(changes_summary)

    if not release_notes:
        print("Failed to generate release notes. Using default notes.")
        release_notes = "Release notes not available."

    # Create a release using gh cli
    release_title = f"War Thunder Camouflage Installer {new_tag}"
    print(f"Creating release: {release_title}")
    
    create_release_command = (
        f'gh release create {new_tag} '
        f'--title "{release_title}" '
        f'--notes "{release_notes}" '
        f'"../war_thunder_camouflages.db" '
        f'"./binaries/war_thunder_camo_installer.exe"'
    )
    output, error, return_code = run_command(create_release_command)
    
    if return_code != 0:
        print(f"Error creating release: {error}")
        print("You may need to create the release manually or check your GitHub CLI configuration.")
    else:
        print("Release created successfully.")
        print(output)

if __name__ == "__main__":
    main()