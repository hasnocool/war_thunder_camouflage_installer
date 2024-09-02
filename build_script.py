import subprocess
import os
import sys
import time
import argparse
import logging
import toml
import configparser
import requests

# Configuration
CARGO_BUILD_OPTIONS = "--release -j50"
DEFAULT_BUILD_INTERVAL = 3600  # 1 hour
CONFIG_FILE = "config.ini"
OLLAMA_MODEL = "llama3"
OLLAMA_API_URL = "http://192.168.1.223:11434"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "wtci_db", "war_thunder_camouflages.db")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB in bytes

# Update these variables with your correct repository information
GITHUB_REPO_OWNER = "hasnocool"  # Replace with your GitHub username
GITHUB_REPO_NAME = "war_thunder_camouflage_installer"  # Replace with your repository name

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, verbose=True):
    if verbose:
        print(f"Running command: {command}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, universal_newlines=True)
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

    # Attempt to push changes
    code, output, error = run_command("git push --no-verify", verbose=True)

    if code != 0:
        logger.error(f"Failed to push changes: {error}")
        return code, output, error

    return code, output, error


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
        with open(os.path.join(SCRIPT_DIR, "Cargo.toml"), "r") as f:
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

def create_release(auto_confirm=False):
    logger.info("Creating a new release...")
    
    # Generate release notes (you can modify this to generate more detailed notes)
    release_notes = "New release with updated executable and database."

    # Get the executable file path
    project_name, error = get_project_info()
    if not project_name:
        logger.error(f"Failed to get project name: {error}")
        return False
    
    executable_path = os.path.join(SCRIPT_DIR, "target", "release", f"{project_name}.exe")

    # Check if files exist
    if not os.path.exists(executable_path):
        logger.error(f"Executable not found at {executable_path}")
        return False
    if not os.path.exists(DB_FILE_PATH):
        logger.error(f"Database file not found at {DB_FILE_PATH}")
        return False

    # Files to include in the release
    files_to_release = []
    for file_path in [executable_path, DB_FILE_PATH]:
        file_size = os.path.getsize(file_path)
        if file_size <= MAX_FILE_SIZE:
            files_to_release.append(file_path)
        else:
            logger.warning(f"Skipping {file_path} (size: {file_size / 1024 / 1024:.2f}MB) as it exceeds GitHub's 100MB limit")

    if not files_to_release:
        logger.error("No files to release after size check")
        return False

    files_to_release_str = ' '.join(f'"{file}"' for file in files_to_release)

    # Create a unique tag for the release
    release_tag = f'v{time.strftime("%Y.%m.%d")}-{time.strftime("%H%M%S")}'

    # Create the release using GitHub CLI
    release_command = f'gh release create {release_tag} {files_to_release_str} --notes "{release_notes}"'
    code, output, error = run_command(release_command, verbose=True)

    if code == 0:
        logger.info(f"Release created successfully with tag: {release_tag}")
        return True
    else:
        logger.error(f"Failed to create release: {error}")
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

    code, output, error = cargo_test(auto_confirm)
    if code != 0:
        logger.error(f"Tests failed: {error}")
        return False

    code, output, error = git_commit_and_push(auto_confirm, use_ollama)
    if code != 0:
        logger.error(f"Failed to commit and push: {error}")
        return False

    if not create_release(auto_confirm):
        logger.error("Failed to create release.")
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