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

#ORG = 'quest-im'
#TOKEN = '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'

# Set up metrics
gha_run_duration = Gauge('github_actions_run_duration_seconds', 'Duration of runs for a given workflow', ['repo', 'workflow'])
gha_run_status = Gauge('github_actions_run_status', 'Status of GitHub Actions workflow run', ['repo', 'workflow', 'status', 'updated_at', 'duration'])

def get_repos(org: str, TOKEN: str):
    url = f"https://api.github.com/orgs/{org}/repos"
    headers = {'Authorization': f'token {TOKEN}'}
    r = requests.get(url, headers=headers)
    if r.status_code == 401:
        logger.error("Failed to authenticate with GitHub API - check your token")
    if r.status_code == 403:
        logger.error("API rate limit exceeded")
        check_limits()
        return []
    if r.status_code != 200:
        logger.error(f"Request failed with status code {r.status_code} and message: {r.text}")
        return []
    data = r.json()
    return [repo['full_name'] for repo in data]


def get_workflows(repo: str):
    url = f"https://api.github.com/repos/{repo}/actions/workflows"
    headers = {'Authorization': f'token {TOKEN}'}
    r = requests.get(url, headers=headers)
    if r.status_code == 401:
        logger.error("Failed to authenticate with GitHub API - check your token")
    if r.status_code != 200:
        logger.error(f"Request failed with status code {r.status_code} and message: {r.text}")
        return []
    data = r.json()
    if 'workflows' in data:
        return [(workflow['id'], workflow['name']) for workflow in data['workflows']]
    else:
        return []


def get_workflow_runs(repo: str, workflow_id: str, branch: str, TOKEN: str):
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/runs?per_page=10&branch={branch}&sort=run_number&direction=desc"
    headers = {'Authorization': f'token {TOKEN}'}
    r = requests.get(url, headers=headers)
    if r.status_code == 401:
        logger.error("Failed to authenticate with GitHub API - check your token")
    if r.status_code != 200:
        logger.error(f"Request failed with status code {r.status_code} and message: {r.text}")
        return []
    data = r.json()
    runs = data['workflow_runs']
    # Sort runs in ascending order by updated_at
    sorted_runs = sorted(runs, key=lambda run: run['updated_at'], reverse=True)
    return [{'id': run['id'], 'status': run['conclusion'], 'created_at': run['created_at'], 'updated_at': run['updated_at']} for run in sorted_runs]

def update_metrics():
    repos = get_repos(ORG, TOKEN)
    for repo in repos:
        workflows = get_workflows(repo)
        for workflow_id, workflow_name in workflows:
            #if repo == 'quest-im/foglight-demo-sandbox' and (workflow_name == 'Remote action' or workflow_name == 'Greetings'):
                #continue  # Skip these workflows
            runs = get_workflow_runs(repo, workflow_id, "main", TOKEN)
            if runs:
                last_run = runs[0]
                last_run_status  = last_run['status']
                created_at = datetime.strptime(last_run['created_at'][:-1], '%Y-%m-%dT%H:%M:%S')
                updated_at = datetime.strptime(last_run['updated_at'][:-1], '%Y-%m-%dT%H:%M:%S')
                duration = (updated_at - created_at).total_seconds()
                gha_run_status.labels(repo=repo, workflow=workflow_name, status=last_run_status, updated_at=updated_at, duration=duration).inc()
                gha_run_duration.labels(repo=repo, workflow=workflow_name).set(duration)

def check_limits():
    headers = {'Authorization': f'token {TOKEN}'}

    response = requests.get('https://api.github.com/rate_limit', headers=headers)

    remaining_requests = int(response.headers['X-RateLimit-Remaining'])
    reset_time = datetime.fromtimestamp(int(response.headers['X-RateLimit-Reset']))

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
