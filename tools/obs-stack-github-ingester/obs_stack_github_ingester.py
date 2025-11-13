import json
import logging
import subprocess
import time

import requests

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

REMOTE_URL = "https://github.com/dfinity/ic-observability-stack.git"


def _run_git_command(args):
    """
    Run a git command and return its stripped output.
    """
    try:
        result = subprocess.run(
            ["git"] + args, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error("Git command failed: %s", e.stderr.strip())
        return None


def get_installed_commit():
    """
    Get the current commit hash.
    """
    commit = _run_git_command(["rev-parse", "HEAD"])
    if commit:
        logging.debug("Installed commit: %s", commit)
    return commit


def get_local_state():
    """
    Clean or Dirty.

    If there are any uncommited changes.
    """
    status = _run_git_command(["status", "--porcelain"])
    state = "Clean" if not status else "Dirty"
    logging.debug("Local repository state: %s", state)

    return state


def get_remote_commit_hash():
    """
    Get the latest commit from remote origin.
    """
    output = _run_git_command(["ls-remote", REMOTE_URL, "refs/heads/master"])
    if not output:
        return "Unknown"

    commit = output.split()[0]
    logging.debug("Remote head commit: %s", commit)

    return commit


def get_commits_difference(local_commit, remote_commit):
    """
    Get the difference from installed and remote commit.

    Note: it is possible that the current branch has
    a commit which isn't present on remote which should
    be accounted for.
    """
    local_origin_commit = _run_git_command(["rev-parse", "refs/remotes/origin/master"])

    if not all([local_commit, local_origin_commit, remote_commit]):
        logging.warning(
            "Cannot determine commits (missing refs): local_commit = %s, remote_commit = %s and local_origin_commit = %s",
            local_commit,
            remote_commit,
            local_origin_commit,
        )
        return {"ahead": "Unknown", "behind": "Unknown"}

    ahead_count = _run_git_command(
        ["rev-list", "--count", f"{local_origin_commit}..{local_commit}"]
    )

    api_url = f"https://api.github.com/repos/dfinity/ic-observability-stack/compare/{local_origin_commit}...{remote_commit}"
    response = requests.get(
        api_url,
        headers={
            "User-Agent": "python",
        },
        timeout=10,
    )
    try:
        response.raise_for_status()
    except Exception:
        logging.error("Failed to fetch diff from remote: %s", response.text)
        return {"ahead": ahead_count, "behind": "Unknown"}

    logging.debug(
        "Complete response from github:\n%s", json.dumps(response.json(), indent=4)
    )

    behind_count = response.json()["behind_by"]

    return {"ahead": ahead_count, "behind": behind_count}


def main():
    logging.info("Running obs stack github ingester")

    # Only fetch installed commit on startup
    installed_commit = get_installed_commit()

    while True:
        state = get_local_state()

        remote_commit = get_remote_commit_hash()

        difference = get_commits_difference(installed_commit, remote_commit)

        logging.info("Current difference:\n%s", json.dumps(difference, indent=4))
        logging.info("Sleeping for 30 minutes")

        time.sleep(30 * 60)


if __name__ == "__main__":
    main()
