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
OLLAMA_API_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama2"

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
    try:
        prompt = (
            "Based on the following changes in the source files and Cargo.toml, "
            "generate a concise and factual commit message summarizing these updates. "
            "Only provide the commit message, nothing else.\n\n"
            "Example commit message format:\n"
            "- Refactored API endpoints to improve performance and scalability.\n"
            "- Added error handling to enhance debugging capabilities.\n"
            "- Fixed UI alignment issue on the dashboard (Fixes #234).\n"
            "- Updated Cargo dependencies to the latest stable versions.\n\n"
            f"Changes summary:\n{changes_summary}"
        )

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(f"{OLLAMA_API_URL}/api/generate", json=payload, headers=headers)
        response.raise_for_status()
        
        print(f"Raw response from Ollama: {response.text}")
        
        commit_message = response.json().get("response", "").strip()
        logger.info(f"Generated commit message: {commit_message}")
        return commit_message
    except requests.RequestException as e:
        logger.error(f"Error generating commit message with Ollama: {e}")
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

    print(f"Creating new tag: {new_tag}")

    # Create the new tag
    _, error, _ = run_command(f'git tag {new_tag}')
    if error:
        print(f"Error creating tag: {error}")
        return

    # Try to push the new tag
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
    
    create_release_command = f'gh release create {new_tag} --title "{release_title}" --notes "{release_notes}"'
    output, error, return_code = run_command(create_release_command)
    
    if return_code != 0:
        print(f"Error creating release: {error}")
        print("You may need to create the release manually or check your GitHub CLI configuration.")
    else:
        print("Release created successfully.")
        print(output)

if __name__ == "__main__":
    main()