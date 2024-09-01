import subprocess
import os
import sys
import time
import argparse
import logging

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