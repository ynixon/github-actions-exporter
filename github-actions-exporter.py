#!/usr/bin/env python3
from prometheus_client import start_http_server, Gauge
import requests
import time
from datetime import datetime
import argparse
import yaml
import logging
import sys
import traceback
from datetime import timedelta

parser = argparse.ArgumentParser()
parser.add_argument('--config-file', help='Path to configuration file')
args = parser.parse_args()
logger = logging.getLogger(__name__)

if args.config_file:
    with open(args.config_file, 'r') as f:
        config = yaml.safe_load(f.read())
        ORG = config.get('org', '')
        TOKEN = config.get('token', '')
        PORT = config.get('port', '')

# Set up metrics
gha_run_status = Gauge('github_actions_run_status', 'Status of GitHub Actions workflow run', [
                       'repo', 'workflow', 'status', 'updated_at', 'duration', 'user'])

session = requests.Session()
session.headers.update({'Authorization': f'token {TOKEN}'})

def get_repos(org: str, TOKEN: str):
    url = f"https://api.github.com/orgs/{org}/repos"
    try:
        r = session.get(url)
        r.raise_for_status()
        data = r.json()
        return [repo['full_name'] for repo in data]
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        check_limits()
        return []

def get_workflows(repo: str):
    url = f"https://api.github.com/repos/{repo}/actions/workflows"
    try:
        r = session.get(url)
        r.raise_for_status()
        data = r.json()
        if 'workflows' in data:
            return [(workflow['id'], workflow['name']) for workflow in data['workflows'] if workflow['state'] != 'disabled_manually']
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return []

def get_workflow_runs(repo: str, workflow_id: str, branch: str, TOKEN: str):
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/runs?per_page=10&branch={branch}&sort=run_number&direction=desc"
    try:
        r = session.get(url)
        r.raise_for_status()
        data = r.json()
        runs = data['workflow_runs']
        # Sort runs in ascending order by updated_at
        sorted_runs = sorted(runs, key=lambda run: run['updated_at'], reverse=True)
        return [{'id': run['id'], 'status': run["conclusion"] if run["conclusion"] else "N/A", 'created_at': run['created_at'], 'updated_at': run['updated_at'], 'user': "scheduled" if run['event'] == 'schedule' else run['actor']['login']} for run in sorted_runs]

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return []

def update_metrics():
    repos = get_repos(ORG, TOKEN)
    for repo in repos:
        workflows = get_workflows(repo)
        for workflow_id, workflow_name in workflows:
            # if repo == 'quest-im/foglight-demo-sandbox' and (workflow_name == 'Remote action' or workflow_name == 'Greetings'):
            # continue  # Skip these workflows
            runs = get_workflow_runs(repo, workflow_id, "main", TOKEN)
            if runs:
                last_run = runs[0]
                last_run_status = last_run['status']
                user = last_run["user"]
                created_at = datetime.strptime(
                    last_run['created_at'][:-1], '%Y-%m-%dT%H:%M:%S')
                updated_at = datetime.strptime(
                    last_run['updated_at'][:-1], '%Y-%m-%dT%H:%M:%S')
                if last_run_status == "N/A":
                   duration = (datetime.now().replace(microsecond=0) - created_at).total_seconds()
                else:
                   duration = (updated_at - created_at).total_seconds()
                #updated_at = updated_at.timestamp()
                gha_run_status.labels(repo=repo, workflow=workflow_name,
                                      status=last_run_status, updated_at=updated_at, duration=timedelta(seconds=duration), user=user).set(updated_at.timestamp())

def check_limits():
    headers = {'Authorization': f'token {TOKEN}'}

    response = requests.get(
        'https://api.github.com/rate_limit', headers=headers)

    remaining_requests = int(response.headers['X-RateLimit-Remaining'])
    reset_time = datetime.fromtimestamp(
        int(response.headers['X-RateLimit-Reset']))

    logging.error(f'You have {remaining_requests} requests remaining.')
    logging.error(f'Your rate limit will reset at {reset_time}.')


def start_http_server_with_error_handling(port):
    try:
        start_http_server(port)
    except OSError as e:
        logging.error(f'Could not start HTTP server on port {port}. {e}')


if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server_with_error_handling(PORT)

    while True:
        try:
            update_metrics()
        except Exception as e:
            tb = traceback.format_exc()
            # This block will catch any uncaught error
            logging.error(f"An error occurred: {e}\n{tb}")
            sys.exit(1)
        time.sleep(60)
