import subprocess
import os
import sys
import time
import argparse
import logging
import shutil
import hashlib
import toml
import configparser
import requests
from bs4 import BeautifulSoup
from packaging import version

# Configuration
CARGO_BUILD_OPTIONS = "--release -j50"
DEFAULT_BUILD_INTERVAL = 3600  # 1 hour
CONFIG_FILE = "config.ini"
OLLAMA_MODEL = "llama3"
OLLAMA_API_URL = "http://192.168.1.223:11434"
DB_FOLDER = "db"
DB_FILE = os.path.join(DB_FOLDER, "war_thunder_camouflages.db")
BINARIES_FOLDER = "binaries"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, verbose=True):
    if verbose:
        print(f"Running command: {command}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, encoding='utf-8', errors='ignore')
    output, error = process.communicate()
    return process.returncode, output, error

def authenticate_github():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    if 'github' not in config or 'token' not in config['github']:
        logger.error("GitHub token not found in config.ini. Please add your GitHub token.")
        sys.exit(1)

    github_token = config['github']['token']

    logger.info("Authenticating with GitHub using gh CLI...")
    code, output, error = run_command(f'echo {github_token} | gh auth login --with-token', verbose=True)
    
    if code != 0:
        logger.error(f"Failed to authenticate with GitHub: {error}")
        sys.exit(1)
    
    logger.info("Successfully authenticated with GitHub.")

def check_dependencies(auto_confirm=True):
    logger.info("Checking for required dependencies...")
    for cmd in ['git --version', 'cargo --version', 'gh --version']:
        code, output, error = run_command(cmd, verbose=True)
        if code != 0:
            logger.error(f"Dependency check failed for command: {cmd}. Error: {error}")
            sys.exit(1)
    print("All dependencies are installed.")

def git_pull(auto_confirm=True):
    logger.info("Pulling latest changes...")
    code, output, error = run_command("git pull", verbose=True)
    
    if code != 0 and "Your local changes to the following files would be overwritten by merge" in error:
        logger.warning("Local changes detected that would be overwritten by merge.")
        if not auto_confirm and not prompt_user("Local changes detected. Do you want to automatically commit these changes? (y/n)"):
            return code, output, error

        logger.info("Automatically committing or stashing local changes...")
        
        code, output, error = run_command("git status --porcelain", verbose=False)
        if output.strip():
            run_command("git add .", verbose=True)
            run_command('git commit -m "Auto-commit before pulling latest changes"', verbose=True)
        else:
            run_command("git stash", verbose=True)

        code, output, error = run_command("git pull", verbose=True)
        if code == 0:
            logger.info("Successfully pulled latest changes after handling local changes.")
        else:
            logger.error(f"Failed to pull latest changes even after handling local changes: {error}")

    elif code != 0:
        logger.error(f"Failed to pull latest changes: {error}")

    return code, output, error

def cargo_build(auto_confirm=True):
    logger.info(f"Building project with options: {CARGO_BUILD_OPTIONS}")
    if not auto_confirm and not prompt_user("Do you want to build the project?"):
        return (0, "", "")
    return run_command(f"cargo build {CARGO_BUILD_OPTIONS}", verbose=True)

def cargo_test(auto_confirm=True):
    logger.info("Running tests...")
    if not auto_confirm and not prompt_user("Do you want to run the tests?"):
        return (0, "", "")
    return run_command("cargo test", verbose=True)

def generate_detailed_changes_summary():
    try:
        run_command("git fetch", verbose=True)

        code, branches_output, _ = run_command("git branch -r", verbose=True)
        if code != 0:
            logger.error("Failed to retrieve remote branches.")
            return ""

        remote_branch = None
        for line in branches_output.splitlines():
            if 'origin/main' in line:
                remote_branch = 'origin/main'
                break
            elif 'origin/master' in line:
                remote_branch = 'origin/master'
                break

        if not remote_branch:
            logger.error("No valid remote branch found (e.g., origin/main or origin/master).")
            return ""

        code, output, _ = run_command(f"git diff {remote_branch} -- src/ Cargo.toml", verbose=True)
        if code != 0:
            logger.error("Failed to get the diff of modified files against the remote.")
            return ""

        if not output.strip():
            logger.info("No changes detected between the local and remote repository.")
            return "No changes detected."

        changes_summary = output.strip()
        logger.info(f"Generated detailed changes summary for Ollama:\n{changes_summary}")
        return changes_summary
    except Exception as e:
        logger.error(f"Error generating detailed changes summary: {e}")
        return ""

def generate_release_args_with_ollama():
    try:
        prompt = (
            "Generate a title and description for a GitHub release based on the following context:\n"
            "- The release is for a database file update related to the War Thunder Camouflage Installer.\n"
            "- Include relevant details about what the update contains or improves.\n"
            "Provide the title and description in a clear format.\n"
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
        
        title, description = response.json().get("response", "").split('\n', 1)
        logger.info(f"Generated release title: {title.strip()}")
        logger.info(f"Generated release description: {description.strip()}")
        return title.strip(), description.strip()
    except requests.RequestException as e:
        logger.error(f"Error generating release arguments with Ollama: {e}")
        return "Database Update Release", "Contains the latest version of the database file."

def git_commit_and_push(auto_confirm=False, use_ollama=False):
    logger.info("Committing and pushing changes...")
    
    # Check if there are any changes to commit
    code, output, error = run_command("git status --porcelain", verbose=False)
    if not output.strip():
        logger.info("No changes to commit.")
        return (0, "", "")
    
    changes_summary = generate_detailed_changes_summary()

    if changes_summary == "No changes detected.":
        commit_message = "Automated commit: No changes detected, repository updated."
    else:
        commit_message = "Automated build commit"

        if use_ollama:
            logger.info("Generating commit message using Ollama...")
            commit_message = generate_commit_message_with_ollama(changes_summary)
            if not commit_message:
                logger.error("Failed to generate commit message using Ollama. Using default commit message.")
                commit_message = "Automated build commit"

    run_command("git add .", verbose=True)
    run_command(f'git commit -m "{commit_message}"', verbose=True)

    # Attempt to push changes, handling large file errors
    code, output, error = run_command("git push --no-verify", verbose=True)

    if code != 0:
        if "large files detected" in error.lower() or "exceeds github's file size limit" in error.lower():
            logger.warning("Large file detected. Excluding from push and proceeding with GitHub release upload.")
            run_command(f"git rm --cached {DB_FILE}", verbose=True)  # Remove the large file from git tracking
            run_command("git commit -m 'Remove large db file from git tracking'", verbose=True)
            run_command("git push --no-verify", verbose=True)  # Retry pushing without the large file
            upload_db_to_github_release(auto_confirm)  # Upload the large file to GitHub Releases
        else:
            logger.error(f"Failed to push changes: {error}")
            return code, output, error

    return code, output, error

def get_file_checksum(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Update these variables with your correct repository information
GITHUB_REPO_OWNER = "hasnocool"  # Replace with your GitHub username
GITHUB_REPO_NAME = "war_thunder_camouflage_installer"  # Replace with your repository name

def get_latest_release_checksum():
    try:
        response = requests.get(f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest")
        response.raise_for_status()
        release_data = response.json()
        for asset in release_data.get("assets", []):
            if asset["name"] == os.path.basename(DB_FILE):
                logger.info(f"Found existing database file in release: {asset['name']}")
                return asset.get("checksum", "")
        logger.info("No existing database file found in the latest release.")
        return ""
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve latest release data: {e}")
        logger.error(f"Make sure the repository '{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}' exists and you have access to it.")
        return ""
    
def upload_db_to_github_release(auto_confirm=False):
    logger.info("Uploading database file to GitHub release...")

    if not os.path.exists(DB_FILE):
        logger.error(f"Database file '{DB_FILE}' not found. Ensure the file path is correct.")
        return False

    local_checksum = get_file_checksum(DB_FILE)
    logger.info(f"Local checksum: {local_checksum}")

    latest_checksum = get_latest_release_checksum()

    if local_checksum == latest_checksum:
        logger.info("Database file has not changed since the last release. Skipping upload.")
        return True

    title, notes = generate_release_args_with_ollama()

    # Remove any markdown formatting from the title
    title = title.replace('*', '').replace('#', '').strip()

    code, output, error = run_command("gh release view latest", verbose=False)
    
    if code != 0:
        logger.info("No 'latest' release found. Creating a new release.")
        code, output, error = run_command(f"gh release create latest --title '{title}' --notes '{notes}' {DB_FILE}", verbose=True)
        if code != 0:
            logger.error(f"Failed to create a new release: {error}")
            logger.error(f"Make sure the file '{DB_FILE}' exists and you have write permissions.")
            return False
    else:
        logger.info("'Latest' release found. Updating the existing release.")
        code, output, error = run_command(f"gh release upload latest '{DB_FILE}' --clobber", verbose=True)
    
    if code == 0:
        logger.info(f"Successfully uploaded {DB_FILE} to the 'latest' release.")
        return True
    else:
        logger.error(f"Failed to upload {DB_FILE} to the 'latest' release: {error}")
        return False


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

def get_project_info():
    try:
        with open("Cargo.toml", "r") as f:
            cargo_toml = toml.load(f)
        project_name = cargo_toml["package"]["name"]
        return project_name, None
    except Exception as e:
        logger.error(f"Error reading Cargo.toml: {e}")
        return None, str(e)

def copy_executable(auto_confirm=False):
    logger.info("Copying executable to binaries folder...")
    if not os.path.exists(BINARIES_FOLDER):
        os.makedirs(BINARIES_FOLDER)

    project_name, error = get_project_info()
    if not project_name:
        logger.error(f"Failed to get project name: {error}")
        return False
    
    source_path = os.path.join("target", "release", f"{project_name}.exe")
    destination_path = os.path.join(BINARIES_FOLDER, f"{project_name}.exe")
    
    if not os.path.exists(source_path):
        logger.error(f"Executable not found at {source_path}")
        return False
    
    try:
        shutil.copy(source_path, destination_path)
        logger.info(f"Executable copied successfully to {destination_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy executable: {e}")
        return False

def build_cycle(auto_confirm=False, use_ollama=False):
    logger.info(f"Starting build cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    code, output, error = git_pull(auto_confirm)
    if code != 0:
        logger.error(f"Failed to pull latest changes: {error}")
        return False

    code, output, error = cargo_build(auto_confirm)
    if code != 0:
        logger.error(f"Build failed: {error}")
        return False

    if not copy_executable(auto_confirm):
        logger.error("Failed to copy executable to binaries folder.")
        return False

    code, output, error = cargo_test(auto_confirm)
    if code != 0:
        logger.error(f"Tests failed: {error}")
        return False

    code, output, error = git_commit_and_push(auto_confirm, use_ollama)
    if code != 0:
        logger.error(f"Failed to commit and push: {error}")
        return False

    if not upload_db_to_github_release(auto_confirm):
        logger.error("Failed to upload database file to GitHub release.")
        return False

    logger.info("Build cycle completed successfully!")
    return True

def prompt_user(message):
    while True:
        response = input(f"{message} ").lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please answer with 'y' or 'n'.")

def main(daemon_mode, build_interval, auto_confirm, use_ollama):
    authenticate_github()
    check_dependencies(auto_confirm)

    while True:
        success = build_cycle(auto_confirm, use_ollama)
        if not daemon_mode:
            sys.exit(0 if success else 1)
        logger.info(f"Waiting for next build cycle. Next build at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + build_interval))}")
        time.sleep(build_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Continuous build pipeline for Rust project")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode (continuous building)")
    parser.add_argument("--interval", type=int, default=DEFAULT_BUILD_INTERVAL, help="Build interval in seconds (for daemon mode)")
    parser.add_argument("--yes", "-y", action="store_true", help="Automatically say yes to all prompts")
    parser.add_argument("--use-ollama", action="store_true", help="Use Ollama API to generate commit messages")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    use_ollama = config.getboolean('ollama', 'use_ollama', fallback=False) or args.use_ollama

    try:
        main(args.daemon, args.interval, args.yes, use_ollama)
    except KeyboardInterrupt:
        logger.info("\nBuild pipeline stopped by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)