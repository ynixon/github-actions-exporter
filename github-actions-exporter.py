#!/usr/bin/env python3
from prometheus_client import start_http_server, Gauge
import requests
import time
from datetime import datetime, timedelta
import argparse
import yaml
import logging
import sys
import traceback
import re

# Set up argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("--config-file", help="Path to configuration file")
parser.add_argument("--debug", action="store_true", help="Enable debug logging")
args = parser.parse_args()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if args.debug else logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(console_handler)

file_handler = logging.FileHandler(
    "/var/log/github-actions/github-actions-exporter.log"
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)

if args.debug:
    debug_file_handler = logging.FileHandler("github_actions_exporter_debug.log")
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(debug_file_handler)

# Load configuration
if args.config_file:
    with open(args.config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f.read())
        ORGS = config.get("orgs", [])
        PORT = config.get("port", 8000)

# Set up metrics
gha_run_status = Gauge(
    "github_actions_run_status",
    "Status of GitHub Actions workflow run",
    [
        "org",
        "repo",
        "workflow",
        "status",
        "conclusion",
        "updated_at",
        "duration",
        "user",
        "branch",
    ],
)

session = requests.Session()

# Store repositories and workflows with criteria matching
repositories_with_workflows = {}
last_repo_fetch_time = datetime.min

api_calls_used = 0  # Counter for API calls


def should_skip_repo(repo_name: str, skip_phrases: list):
    """
    Determine if a repository should be skipped based on its name using regex.

    Args:
        repo_name (str): The name of the repository.
        skip_phrases (list): List of regex patterns to skip repositories.

    Returns:
        bool: True if the repository should be skipped, False otherwise.
    """
    logger.debug(
        "Checking if repo %s should be skipped with skip phrases: %s",
        repo_name,
        skip_phrases,
    )
    for phrase in skip_phrases:
        if re.search(phrase, repo_name, re.IGNORECASE):
            logger.debug("Skipping repo %s due to skip phrase %s", repo_name, phrase)
            return True
    return False


def get_repos(org: str, token: str, skip_phrases: list):
    """
    Fetch all repositories for a given organization.

    Args:
        org (str): The organization name.
        token (str): The GitHub API token.
        skip_phrases (list): List of phrases to skip repositories.

    Returns:
        list: A list of repository full names.
    """
    global api_calls_used  # Use the global counter
    url = f"https://api.github.com/orgs/{org}/repos"
    session.headers.update({"Authorization": f"token {token}"})
    repos = []
    page = 1

    while True:
        try:
            r = session.get(url, params={"page": page, "per_page": 100}, timeout=10)
            r.raise_for_status()
            api_calls_used += 1  # Increment API call counter
            data = r.json()
            for repo in data:
                logger.debug("Checking repo: %s", repo["full_name"])
                if not should_skip_repo(repo["full_name"], skip_phrases):
                    repos.append(repo["full_name"])
                else:
                    logger.debug("Repo %s is skipped", repo["full_name"])
            if "Link" not in r.headers or 'rel="next"' not in r.headers["Link"]:
                break
            page += 1
        except requests.exceptions.RequestException as request_exception:
            logger.error("Request failed for org %s: %s", org, request_exception)
            check_limits(token)
            break
    return repos


def get_workflows(repo: str, token: str):
    """
    Fetch all workflows for a given repository.

    Args:
        repo (str): The repository full name.
        token (str): The GitHub API token.

    Returns:
        list: A list of tuples containing workflow ID and name.
    """
    global api_calls_used  # Use the global counter
    url = f"https://api.github.com/repos/{repo}/actions/workflows"
    session.headers.update({"Authorization": f"token {token}"})
    try:
        r = session.get(url, timeout=10)
        r.raise_for_status()
        api_calls_used += 1  # Increment API call counter
        data = r.json()
        if "workflows" in data:
            return [
                (workflow["id"], workflow["name"])
                for workflow in data["workflows"]
                if workflow["state"] != "disabled_manually"
            ]
    except requests.exceptions.RequestException as request_exception:
        logger.error("Request failed for repo %s: %s", repo, request_exception)
        check_limits(token)
        return []
    return []


def get_latest_workflow_run(repo: str, workflow_id: str, branch: str, token: str):
    """
    Fetch the latest workflow run for a given repository and workflow.

    Args:
        repo (str): The repository full name.
        workflow_id (str): The workflow ID.
        branch (str): The branch name.
        token (str): The GitHub API token.

    Returns:
        dict: The latest workflow run data.
    """
    global api_calls_used  # Use the global counter
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/runs"
    session.headers.update({"Authorization": f"token {token}"})
    try:
        r = session.get(
            url,
            params={
                "per_page": 1,
                "branch": branch,
                "sort": "run_number",
                "direction": "desc",
            },
            timeout=10,
        )
        r.raise_for_status()
        api_calls_used += 1  # Increment API call counter
        data = r.json()
        if data["workflow_runs"]:
            return data["workflow_runs"][0]
    except requests.exceptions.RequestException as request_exception:
        logger.error(
            "Request failed for repo %s, workflow %s: %s",
            repo,
            workflow_id,
            request_exception,
        )
        check_limits(token)
        return None
    return None


def update_metric_for_run(org, repo, workflow_name, run):
    """
    Update Prometheus metrics for a specific workflow run.

    Args:
        org (str): The organization name.
        repo (str): The repository full name.
        workflow_name (str): The workflow name.
        run (dict): The workflow run data.
    """
    status = run["status"]
    conclusion = run.get("conclusion")
    if conclusion is None:
        if status == "in_progress":
            conclusion = "Running"
        elif status == "queued":
            conclusion = "Pending"
        else:
            conclusion = status
    user = run["actor"]["login"] if "actor" in run else "unknown"
    created_at = datetime.strptime(run["created_at"][:-1], "%Y-%m-%dT%H:%M:%S")
    updated_at = datetime.strptime(run["updated_at"][:-1], "%Y-%m-%dT%H:%M:%S")
    duration = (updated_at - created_at).total_seconds()
    gha_run_status.labels(
        org=org,
        repo=repo,
        workflow=workflow_name,
        status=status,
        conclusion=conclusion,
        updated_at=updated_at,
        duration=timedelta(seconds=duration),
        user=user,
        branch=run["head_branch"],
    ).set(updated_at.timestamp())
    logger.debug("Set metric for %s in repo %s", workflow_name, repo)


def get_branch_for_workflow(
    repo: str, workflow_name: str, workflow_branches: dict, skip_workflows: list
):
    """
    Get the branch for a workflow based on the workflow_branches configuration.

    Args:
        repo (str): The repository full name.
        workflow_name (str): The workflow name.
        workflow_branches (dict): The workflow branches configuration.
        skip_workflows (list): List of workflows to skip.

    Returns:
        str: The branch name, or None if it should be skipped.
    """
    # Check if the workflow should be skipped
    if should_skip_workflow(repo, workflow_name, skip_workflows):
        return None

    # Check for exact match first
    if f"{repo}/{workflow_name}" in workflow_branches:
        branch = workflow_branches[f"{repo}/{workflow_name}"]
        if branch is None:
            logger.debug(
                'Found "None" for workflow %s in repo %s, skipping this workflow (exact match)',
                workflow_name,
                repo,
            )
            return None
        logger.debug(
            "Using branch %s for workflow %s in repo %s (exact match)",
            branch,
            workflow_name,
            repo,
        )
        return branch

    # Check for regex match
    for pattern, branch in workflow_branches.items():
        logger.debug(
            "Checking pattern %s for workflow %s in repo %s",
            pattern,
            workflow_name,
            repo,
        )
        if re.match(
            pattern.replace("*", ".*"), f"{repo}/{workflow_name}", re.IGNORECASE
        ):
            if branch is None:
                logger.debug(
                    'Found "None" for workflow %s in repo %s, skipping this workflow (regex match)',
                    workflow_name,
                    repo,
                )
                return None
            logger.debug(
                "Using branch %s for workflow %s in repo %s (regex match)",
                branch,
                workflow_name,
                repo,
            )
            return branch

    # Default to 'main' if no match found
    logger.debug(
        "No specific branch found for workflow %s in repo %s, using default branch 'main'",
        workflow_name,
        repo,
    )
    return "main"


def should_skip_workflow(repo, workflow_name, skip_workflows):
    repo_name = repo.split("/")[
        -1
    ]  # Get the actual repository name without the organization prefix
    for skip_item in skip_workflows:
        for skip_repo, skip_workflow in skip_item.items():
            logger.debug(
                "Checking skip rule: repo='%s', workflow='%s'", skip_repo, skip_workflow
            )
            if re.match(skip_workflow.replace("*", ".*"), workflow_name, re.IGNORECASE):
                if skip_repo == "*" or skip_repo == repo_name:
                    logger.debug(
                        'Found "%s" for workflow %s in repo %s, skipping this workflow',
                        skip_workflow,
                        workflow_name,
                        repo,
                    )
                    return True
                else:
                    logger.debug(
                        "Repo %s does not match skip rule %s", repo_name, skip_repo
                    )
    return False


def update_metrics():
    global last_repo_fetch_time, repositories_with_workflows, api_calls_used

    if (datetime.now() - last_repo_fetch_time).total_seconds() >= 3600:
        logger.info("Fetching repositories for all organizations")
        repositories_with_workflows = {}
        for org in ORGS:
            org_name = org["name"]
            token = org["token"]
            skip_repositories_pattern = org.get("skip_repositories_pattern", [])
            skip_workflows = org.get("skip_workflows", [])
            workflow_branches = org.get("workflow_branches", {})
            repos = get_repos(org_name, token, skip_repositories_pattern)
            logger.debug("Fetched repositories for org %s: %s", org_name, repos)
            for repo in repos:
                workflows = get_workflows(repo, token)
                logger.debug("Fetched workflows for repo %s: %s", repo, workflows)
                for workflow_id, workflow_name in workflows:
                    branch = get_branch_for_workflow(
                        repo, workflow_name, workflow_branches, skip_workflows
                    )
                    if branch is None:
                        logger.debug(
                            "Skipping workflow %s from repo %s", workflow_name, repo
                        )
                        continue
                    if org_name not in repositories_with_workflows:
                        repositories_with_workflows[org_name] = []
                    repositories_with_workflows[org_name].append(
                        (repo, workflow_id, workflow_name, branch)
                    )
        last_repo_fetch_time = datetime.now()

    logger.info("Updating metrics for repositories with workflows")
    for org_name, workflows in repositories_with_workflows.items():
        token = next(org["token"] for org in ORGS if org["name"] == org_name)
        for repo, workflow_id, workflow_name, branch in workflows:
            logger.debug(
                "Processing workflow %s in repo %s on branch %s",
                workflow_name,
                repo,
                branch,
            )
            latest_run = get_latest_workflow_run(repo, workflow_id, branch, token)
            logger.debug(
                "Fetched latest workflow run for %s in repo %s: %s",
                workflow_name,
                repo,
                latest_run,
            )
            if latest_run:
                update_metric_for_run(org_name, repo, workflow_name, latest_run)


def check_limits(token: str):
    """
    Check the GitHub API rate limits and sleep if necessary.

    Args:
        token (str): The GitHub API token.
    """
    headers = {"Authorization": f"token {token}"}
    response = requests.get(
        "https://api.github.com/rate_limit", headers=headers, timeout=10
    )
    data = response.json()
    remaining_requests = data["rate"]["remaining"]
    reset_time = datetime.fromtimestamp(data["rate"]["reset"])
    logger.info(
        "Remaining requests: %d, will reset at %s", remaining_requests, reset_time
    )
    if remaining_requests < 10:
        sleep_seconds = (reset_time - datetime.now()).total_seconds() + 1
        logger.warning(
            "Rate limit will reset in %d seconds. Sleeping...", sleep_seconds
        )
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    start_http_server(int(PORT))
    logger.info("Starting HTTP server on port %d", PORT)
    while True:
        try:
            update_metrics()
        except Exception as main_exception:
            logger.error("An error occurred: %s", main_exception)
            logger.error(traceback.format_exc())
        logger.info(
            "API calls used in this cycle: %d", api_calls_used
        )  # Log API calls used
        api_calls_used = 0  # Reset the counter
        time.sleep(
            240
        )  # interval 4 minutes to limit the API calls per hour to be less than 5000
