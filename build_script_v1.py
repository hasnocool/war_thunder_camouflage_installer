import os
import subprocess
import requests
import logging
import re
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3-chatqa:latest"

def run_command(command):
    """Run a command and return its output and error (if any)."""
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def increment_version(version):
    """Increment the patch version number while preserving the existing suffix."""
    # Split the version into numeric and suffix parts
    if '-' in version:
        base_version, suffix = version.split('-', 1)  # Split into base version and suffix
    else:
        base_version = version
        suffix = None

    parts = base_version.split('.')

    # Increment the patch version part
    if len(parts) >= 3:
        parts[2] = str(int(parts[2]) + 1)  # Convert to int, increment, convert back to str

    new_version = '.'.join(parts)

    # Preserve the suffix if it exists
    if suffix:
        return f"{new_version}-{suffix}"
    return new_version

def check_repo_status():
    """Check if there are uncommitted changes."""
    _, _, return_code = run_command('git diff-index --quiet HEAD --')
    return return_code == 0

def generate_text_with_ollama(prompt):
    """Generate text using Ollama LLM based on a provided prompt."""
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt
            }
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Ollama API: {e}")
        return None

    # Manually parse the concatenated JSON objects
    try:
        content = response.content.decode('utf-8')
        json_objects = content.splitlines()
        full_response = ''.join([json.loads(obj)['response'] for obj in json_objects if obj.strip()])
        return full_response.strip()
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError: {e}")
        logger.error(f"Response content: {response.content.decode('utf-8')}")
        return None

def generate_commit_message(diff_output):
    """Generate a commit message using Ollama LLM based on the git diff output."""
    prompt = (
        "You are an AI assistant that helps generate concise and informative commit messages "
        "for a software repository. The repository is a Rust project that is being maintained "
        "by multiple developers. Please read the following git diff output and generate a "
        "commit message that is clear, concise, and follows the conventional commit style. "
        "The commit message should start with a capitalized verb in the imperative mood and "
        "should not exceed 50 characters in the subject line.\n\n"
        f"Git Diff Output:\n{diff_output}\n\n"
        "Expected Output:\n- A single-line commit subject.\n- An optional commit body with a "
        "brief description of the changes, if necessary."
    )
    
    return generate_text_with_ollama(prompt)

def generate_release_description(change_log):
    """Generate a release description using Ollama LLM based on the changelog."""
    prompt = (
        "You are an AI assistant that helps generate release descriptions for a software repository. "
        "The repository is a Rust project maintained by multiple developers. Please read the following "
        "changelog of recent commits and generate a detailed and informative release description. "
        "The description should summarize the changes, new features, and fixes in a clear and concise manner.\n\n"
        f"Changelog:\n{change_log}\n\n"
        "Expected Output:\n- A detailed description of the release with highlights of the main changes, "
        "new features, and any important fixes."
    )

    return generate_text_with_ollama(prompt)

def handle_large_file_error(error_message):
    """Handle errors related to large files."""
    logger.error(f"Large file error: {error_message}")
    print("Error: A large file error occurred. Please check the log for details.")

def stage_and_commit_changes(commit_message):
    """Stage and commit changes with a generated commit message."""
    run_command('git add .')
    _, error, return_code = run_command(f'git commit -m "{commit_message}"')
    if return_code != 0:
        logger.error("Failed to commit changes: %s", error)
        return False
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

def find_file_recursively(file_name, start_dir='.'):
    """Recursively search for a file starting from a given directory."""
    for root, dirs, files in os.walk(start_dir):
        if file_name in files:
            return os.path.join(root, file_name)
    return None

def get_latest_version_tag():
    """Get the latest version tag using gh command in the format vX.Y.Z-beta."""
    tags_output, error, return_code = run_command('gh release list --limit 100 --json tagName --jq .[].tagName')
    
    if return_code != 0:
        print(f"Error fetching tags: {error}")
        return None

    # Filter tags that match the 'vX.Y.Z-beta' format
    tags = re.findall(r'v(\d+\.\d+\.\d+)-beta', tags_output)
    if not tags:
        return "v1.0.0-beta"  # Default initial tag

    # Sort the tags by version numbers
    tags.sort(key=lambda s: list(map(int, s.split('.'))))
    latest_version = tags[-1]  # Get the latest version in 'X.Y.Z' format

    return f"v{latest_version}-beta"

def find_next_available_tag(current_tag):
    """Find the next available tag by incrementing the version until a unique tag is found."""
    new_version = increment_version(current_tag[1:])  # Remove the 'v' prefix and increment
    new_tag = f"v{new_version}" if '-beta' in current_tag else f"v{new_version}"

    while tag_exists(new_tag):
        new_version = increment_version(new_version)
        new_tag = f"v{new_version}" if '-beta' in current_tag else f"v{new_version}"

    return new_tag

def tag_exists(tag_name):
    """Check if a git tag exists."""
    _, _, return_code = run_command(f'git rev-parse {tag_name}')
    return return_code == 0

def get_diff_with_remote():
    """Get the git diff between the local repository and the remote GitHub repository."""
    # Fetch the latest changes from GitHub
    run_command('git fetch origin')

    # Get the diff
    diff_output, error, return_code = run_command('git diff origin/master')

    if return_code != 0:
        logger.error("Error generating git diff: %s", error)
        return None

    return diff_output

def get_changelog_since_last_tag():
    """Generate a changelog since the last tag."""
    latest_tag = get_latest_version_tag()
    if not latest_tag:
        logger.error("Unable to determine the latest tag.")
        return None

    changelog, error, return_code = run_command(f'git log {latest_tag}..HEAD --pretty=format:"%h %s"')
    if return_code != 0:
        logger.error("Error generating changelog: %s", error)
        return None

    return changelog

def main():
    # Check if we're in a git repository
    if not os.path.isdir('.git'):
        print("Error: This script must be run from the root of a git repository.")
        return

    # Check for uncommitted changes and commit them if any
    if not check_repo_status():
        print("Uncommitted changes detected. Generating commit message...")

        # Get the diff between local changes and remote
        diff_output = get_diff_with_remote()
        if not diff_output:
            print("Failed to generate diff. Cannot proceed with commit.")
            return

        # Generate commit message based on the diff
        commit_message = generate_commit_message(diff_output)
        if not commit_message:
            print("Failed to generate commit message. Using default message.")
            commit_message = "Update changes."

        # Stage and commit changes
        if not stage_and_commit_changes(commit_message):
            print("Failed to commit changes. Please commit manually and run the script again.")
            return

    # Get the latest version tag and increment it
    current_tag = get_latest_version_tag()
    if not current_tag:
        print("Failed to determine the new tag.")
        return

    new_tag = find_next_available_tag(current_tag)

    print(f"Latest tag will be incremented to: {new_tag}")

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

    # Now update Cargo.toml with the new version
    update_cargo_toml(new_tag[1:])  # Remove 'v' prefix
    
    # Commit the Cargo.toml change
    run_command('git add Cargo.toml')
    run_command(f'git commit -m "Update version to {new_tag} in Cargo.toml"')
    run_command('git push origin master')

    # Generate changelog for release description
    changelog = get_changelog_since_last_tag()
    if not changelog:
        print("Failed to generate changelog. Using default description.")
        release_description = "Release notes not available."
    else:
        release_description = generate_release_description(changelog)
        if not release_description:
            print("Failed to generate release description. Using default description.")
            release_description = "Release notes not available."

    # Search for required files
    camouflage_db_path = find_file_recursively('"D:\wtci_db\war_thunder_camouflages.db"')
    installer_path = find_file_recursively('"D:\wtci\binaries\war_thunder_camo_installer.exe"')

    if not camouflage_db_path or not installer_path:
        print("Required files not found. Please ensure the following files are present:")
        if not camouflage_db_path:
            print("- war_thunder_camouflages.db")
        if not installer_path:
            print("- war_thunder_camo_installer.exe")
        return

    # Create a release using gh cli
    release_title = f"War Thunder Camouflage Installer {new_tag}"
    print(f"Creating release: {release_title}")
    
    create_release_command = (
        f'gh release create {new_tag} '
        f'--title "{release_title}" '
        f'--notes "{release_description}" '
        f'"{camouflage_db_path}" '
        f'"{installer_path}"'
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
