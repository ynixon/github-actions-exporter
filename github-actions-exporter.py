#!/usr/bin/env python3
from prometheus_client import start_http_server, Gauge
import requests
import time
from datetime import datetime
import argparse
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('--config-file', help='Path to configuration file')
args = parser.parse_args()

if args.config_file:
    with open(args.config_file, 'r') as f:
        config = yaml.safe_load(f.read())
        ORG = config.get('org', '')
        TOKEN = config.get('token', '')
        PORT = config.get('port', '')

#ORG = 'quest-im'
#TOKEN = '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'

# Set up metrics
gha_run_count = Gauge('github_actions_run_count', 'Number of runs for a given workflow', ['repo', 'workflow'])
gha_run_duration = Gauge('github_actions_run_duration_seconds', 'Duration of runs for a given workflow', ['repo', 'workflow'])
gha_run_status = Gauge('github_actions_run_status', 'Status of GitHub Actions workflow run', ['repo', 'workflow', 'status'])

def get_repos(org: str, TOKEN: str):
    url = f"https://api.github.com/orgs/{org}/repos"
    headers = {'Authorization': f'token {TOKEN}'}
    r = requests.get(url, headers=headers)
    data = r.json()
    return [repo['full_name'] for repo in data]

def get_workflows(repo: str):
    url = f"https://api.github.com/repos/{repo}/actions/workflows"
    headers = {'Authorization': f'token {TOKEN}'}
    r = requests.get(url, headers=headers)
    data = r.json()
    if 'workflows' in data:
        return [(workflow['id'], workflow['name']) for workflow in data['workflows']]
    else:
        return []


def get_workflow_runs(repo: str, workflow: str, TOKEN: str):
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs?per_page=100"
    headers = {'Authorization': f'token {TOKEN}'}
    r = requests.get(url, headers=headers)
    data = r.json()
    runs = data['workflow_runs']
    run_count = len(runs)
    return run_count, [{'id': run['id'], 'status': run['status'], 'created_at': run['created_at'], 'updated_at': run['updated_at']} for run in runs]

def update_metrics():
    repos = get_repos(ORG, TOKEN)
    for repo in repos:
        workflows = get_workflows(repo)
        for workflow_id, workflow_name in workflows:
            if repo == 'quest-im/foglight-demo-sandbox' and (workflow_name == 'Remote action' or workflow_name == 'Greetings'):
                continue  # Skip these workflows
            run_count, runs = get_workflow_runs(repo, workflow_id, TOKEN)
            gha_run_count.labels(repo=repo, workflow=workflow_name).set(run_count)
            if run_count > 0:
                total_duration = 0
                for run in runs:
                    created_at = datetime.strptime(run['created_at'][:-1], '%Y-%m-%dT%H:%M:%S')
                    updated_at = datetime.strptime(run['updated_at'][:-1], '%Y-%m-%dT%H:%M:%S')
                    duration = (updated_at - created_at).total_seconds()
                    total_duration += duration
                    status = run['status']
                    gha_run_status.labels(repo=repo, workflow=workflow_name, status=status).inc()
                avg_duration = total_duration / run_count
                gha_run_duration.labels(repo=repo, workflow=workflow_name).set(avg_duration)


if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(PORT)
    
while True:
        update_metrics()
        time.sleep(60)
