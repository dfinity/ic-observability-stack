import logging
import os
import subprocess
import time
from urllib.parse import urljoin

import requests

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

REMOTE_URL = "https://github.com/dfinity/ic-observability-stack.git"
VICTORIA_METRICS_URL = os.getenv("VICTORIA_METRICS_URL", "http://localhost:9090")


def wait_for_victoria_metrics(victoria_url):
    """Wait for VictoriaMetrics to be ready"""

    logging.info("Waiting for VictoriaMetrics to be ready...")

    while True:
        try:
            response = requests.get(f"{victoria_url}/-/ready", timeout=5)
            if response.status_code == 200:
                logging.info("✅ VictoriaMetrics is ready")
                return
        except requests.exceptions.RequestException:
            continue

        logging.info(f"  Waiting for VictoriaMetrics at {victoria_url}...")
        time.sleep(2)


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


def get_current_commit():
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
    local_origin_commit = _run_git_command(
        ["merge-base", "HEAD", "refs/remotes/origin/master"]
    )

    if not all([local_commit, local_origin_commit, remote_commit]):
        logging.warning(
            "Cannot determine commits (missing refs): local_commit = %s, remote_commit = %s and local_origin_commit = %s",
            local_commit,
            remote_commit,
            local_origin_commit,
        )
        return {"ahead": "NaN", "behind": "NaN"}

    ahead_count = _run_git_command(
        ["rev-list", "--count", f"{local_origin_commit}..{local_commit}"]
    )

    api_url = f"https://api.github.com/repos/dfinity/ic-observability-stack/compare/{remote_commit}...{local_origin_commit}"
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
        return {"ahead": ahead_count, "behind": "NaN"}

    behind_count = response.json()["behind_by"]

    return {"ahead": ahead_count, "behind": behind_count}


def make_line(metric_name, value, ts, **kwargs):
    """
    Make a prometheus metric line
    """

    return f"{metric_name}{{ {', '.join([f'{key}="{value}"' for key, value in kwargs.items()])}  }} {value} {ts}"


def send_to_victoria(metrics, victoria_url):
    import_url = urljoin(victoria_url.rstrip("/") + "/", "api/v1/import/prometheus")

    response = requests.post(
        import_url,
        data=metrics.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=30,
    )

    try:
        response.raise_for_status()
    except Exception:
        logging.error("Failed to send metrics. Response: %s", response.text)
        return

    logging.info("Successfully sent metrics to victoria")


def ingest_metrics(installed_commit, victoria_url):
    timestamp_ms = int(time.time() * 1000)
    state = get_local_state()

    remote_commit = get_remote_commit_hash()

    # Update the difference from the current commit
    # because state can change during running of the
    # stack.
    difference = get_commits_difference(get_current_commit(), remote_commit)

    metrics = (
        "\n".join(
            [
                make_line(
                    "git_installed_commit", 1, timestamp_ms, commit=installed_commit
                ),
                make_line("git_local_state", 1, timestamp_ms, state=state),
                make_line("git_remote_commit", 1, timestamp_ms, commit=remote_commit),
                make_line("git_commits_ahead", difference["ahead"], timestamp_ms),
                make_line("git_commits_behind", difference["behind"], timestamp_ms),
            ]
        )
        + "\n"
    )

    send_to_victoria(metrics, victoria_url)


def main():
    logging.info("Running obs stack github ingester")

    # Only fetch installed commit on startup
    installed_commit = get_current_commit()

    while True:
        try:
            ingest_metrics(installed_commit, VICTORIA_METRICS_URL)
        except Exception as e:
            logging.error("Something went wrong during last execution: %s", e)

        logging.info("Sleeping for 5 minutes")

        time.sleep(5 * 60)


if __name__ == "__main__":
    main()
