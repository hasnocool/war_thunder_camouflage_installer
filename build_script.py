import subprocess
import os
import sys
import time
import argparse
import logging
import shutil
import toml

# Configuration
CARGO_BUILD_OPTIONS = "--release -j50"
DEFAULT_BUILD_INTERVAL = 3600  # 1 hour

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command):
    logger.info(f"Running command: {command}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    output, error = process.communicate()
    return process.returncode, output, error

def check_dependencies():
    logger.info("Checking for required dependencies...")
    for cmd in ['git --version', 'cargo --version']:
        code, output, error = run_command(cmd)
        if code != 0:
            logger.error(f"Dependency check failed for command: {cmd}. Error: {error}")
            sys.exit(1)

def git_pull():
    logger.info("Pulling latest changes...")
    return run_command("git pull")

def cargo_build():
    logger.info(f"Building project with options: {CARGO_BUILD_OPTIONS}")
    return run_command(f"cargo build {CARGO_BUILD_OPTIONS}")

def cargo_test():
    logger.info("Running tests...")
    return run_command("cargo test")

def git_commit_and_push():
    logger.info("Committing and pushing changes...")
    run_command("git add .")
    run_command('git commit -m "Automated build commit"')
    return run_command("git push")

def get_project_name():
    try:
        with open("Cargo.toml", "r") as f:
            cargo_toml = toml.load(f)
        return cargo_toml['package']['name']
    except Exception as e:
        logger.error(f"Failed to read project name from Cargo.toml: {e}")
        return None

def copy_executable():
    logger.info("Copying executable to current directory...")
    project_name = get_project_name()
    if not project_name:
        return False
    
    source_path = os.path.join("target", "release", f"{project_name}.exe")
    
    if not os.path.exists(source_path):
        logger.error(f"Executable not found at {source_path}")
        return False
    
    try:
        shutil.copy(source_path, ".")
        logger.info(f"Executable copied successfully: {project_name}.exe")
        return True
    except Exception as e:
        logger.error(f"Failed to copy executable: {e}")
        return False

def get_current_version():
    try:
        with open("Cargo.toml", "r") as f:
            cargo_toml = toml.load(f)
        return cargo_toml['package']['version']
    except Exception as e:
        logger.error(f"Failed to read version from Cargo.toml: {e}")
        return None

def create_release():
    version = get_current_version()
    if not version:
        return False

    logger.info(f"Creating release v{version}...")
    code, output, error = run_command(f'git tag -a v{version} -m "Release v{version}"')
    if code != 0:
        logger.error(f"Failed to create git tag: {error}")
        return False

    code, output, error = run_command("git push --tags")
    if code != 0:
        logger.error(f"Failed to push git tag: {error}")
        return False

    logger.info(f"Release v{version} created and pushed successfully")
    return True

def prompt_for_release():
    while True:
        response = input("Do you want to create and push a release? (y/n): ").lower()
        if response in ['y', 'n']:
            return response == 'y'
        print("Please enter 'y' or 'n'.")

def build_cycle():
    logger.info(f"Starting build cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Pull latest changes
    code, output, error = git_pull()
    if code != 0:
        logger.error(f"Failed to pull latest changes: {error}")
        return False
    
    # Build the project
    code, output, error = cargo_build()
    if code != 0:
        logger.error(f"Build failed: {error}")
        return False
    
    # Copy the executable
    if not copy_executable():
        return False
    
    # Run tests
    code, output, error = cargo_test()
    if code != 0:
        logger.error(f"Tests failed: {error}")
        return False
    
    # If we got here, everything succeeded. Commit and push.
    code, output, error = git_commit_and_push()
    if code != 0:
        logger.error(f"Failed to commit and push: {error}")
        return False
    
    logger.info("Build cycle completed successfully!")

    # Prompt for release creation
    if prompt_for_release():
        if create_release():
            logger.info("Release created and pushed successfully!")
        else:
            logger.error("Failed to create and push release.")
    
    return True

def main(daemon_mode, build_interval):
    check_dependencies()
    
    while True:
        success = build_cycle()
        if not daemon_mode:
            sys.exit(0 if success else 1)
        logger.info(f"Waiting for next build cycle. Next build at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + build_interval))}")
        time.sleep(build_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Continuous build pipeline for Rust project")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode (continuous building)")
    parser.add_argument("--interval", type=int, default=DEFAULT_BUILD_INTERVAL, help="Build interval in seconds (for daemon mode)")
    args = parser.parse_args()

    try:
        main(args.daemon, args.interval)
    except KeyboardInterrupt:
        logger.info("\nBuild pipeline stopped by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)