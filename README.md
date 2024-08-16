# GitHub Actions Exporter

**GitHub Actions Exporter** is a Prometheus exporter designed to collect and expose metrics related to GitHub Actions. This tool enables you to monitor and analyze the performance and status of your GitHub Actions workflows, providing valuable insights for maintaining CI/CD pipelines.

## Features

- **Workflow Execution Metrics**: Track the status and execution time of GitHub Actions workflows.
- **Customizable Metrics**: Choose which workflow fields to export as metrics.
- **Docker Support**: Easily deploy the exporter using Docker.

## Getting Started

### Prerequisites

Ensure you have the following installed on your system:

- Python 3.x
- Pip (Python package installer)
- Prometheus (for monitoring)
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/ynixon/github-actions-exporter.git
    cd github-actions-exporter
    ```

2. **Install Python dependencies**:

    Use the provided `requirements.txt` file to install necessary Python packages:

    ```bash
    pip install -r requirements.txt
    ```

3. **Create the `github-actions` user**:

    Ensure that the system has a dedicated `github-actions` user:

    ```bash
    sudo grep github-actions /etc/passwd /etc/group
    ```

    If the user does not exist, create it:

    ```bash
    sudo useradd -r -s /sbin/nologin github-actions
    ```

4. **Setup Configuration**:

    Create the configuration and log directories, and set the correct permissions:

    ```bash
    sudo mkdir -p /etc/github-actions/
    sudo cp github-actions.yml /etc/github-actions/github-actions.yml
    sudo chown -R github-actions:github-actions /etc/github-actions/
    
    sudo mkdir -p /var/log/github-actions/
    sudo chown -R github-actions:github-actions /var/log/github-actions/
    ```

### Editing the `github-actions.yml` File

The `github-actions.yml` file is where you configure the settings for the GitHub Actions Exporter. Here’s a breakdown of each section and how to configure it:

#### Explanation of Each Section:

- **`orgs`**: This section contains configurations for multiple GitHub organizations. Each organization has its own set of settings to define how the exporter should interact with it.
  
- **`name`**: Specifies the name of the GitHub organization. Replace `'organization1'` with the actual name of your GitHub organization.

- **`token`**: This is the GitHub Personal Access Token (PAT) used by the exporter to authenticate API requests. Replace `'your-token'` with your actual GitHub token.

- **`skip_repositories_pattern`**: A list of repository name patterns that the exporter should skip. If there are repositories you don't want to monitor, list them here.

- **`skip_workflows`**: Specifies workflows to skip within certain repositories. You can skip specific workflows in certain repositories or use wildcards (`'*'`) to apply the skip to multiple repositories or workflows.

- **`workflow_branches`**: Defines custom branches for specific workflows. This section allows you to specify which branch the exporter should monitor for a given workflow. If a workflow should run on a branch different from the default, define it here. A `null` value indicates that the default branch will be used.

- **`port`**: The port number on which the exporter will run. By default, it is set to `9171`.

### Running the Exporter

The exporter can run in two modes:

1. **Manual Console Mode**: This is usually good for debugging.

    ```bash
    /usr/bin/python3 /usr/local/bin/github-actions-exporter.py --config-file=/etc/github-actions/github-actions.yml
    ```

2. **As a Service**:

    - Copy the `github-actions-exporter.service` file to `/etc/systemd/system/`:

        ```bash
        sudo cp github-actions-exporter.service /etc/systemd/system/
        ```

    - Enable and start the service:

        ```bash
        sudo systemctl daemon-reload
        sudo systemctl enable github-actions-exporter
        sudo systemctl start github-actions-exporter
        ```

### Using Docker

If you prefer to deploy using Docker, follow these steps:

1. **Build the Docker Image**:

    Navigate to the directory containing your `Dockerfile` and run:

    ```bash
    docker build -t github-actions-exporter .
    ```

2. **Run the Docker Container**:

    Once the image is built, you can run the container with:

    ```bash
    docker run -d -p 9171:9171 --name github-actions-exporter github-actions-exporter
    ```

    This command will start the container and expose the exporter on port `9171`.

### Prometheus Integration

To integrate with Prometheus, add the following configuration to your Prometheus `prometheus.yml` file:

```yaml
scrape_configs:
  - job_name: 'github_actions_exporter'
    static_configs:
      - targets: ['localhost:9171']
```

### Metrics Documentation

The exporter exposes the following metrics:

- **`github_workflow_run_status`**: Status of GitHub Actions workflows (Success, Failure, etc.).
- **`github_workflow_run_duration_ms`**: Execution time of GitHub Actions workflows in milliseconds.
- **`github_runner_status`**: Status of GitHub self-hosted runners (Online, Offline).

### Example Prometheus Queries

Here are some useful Prometheus queries to analyze your GitHub Actions metrics:

- **List All Jobs**:

    ```promql
    topk by (repo, workflow) (1,
      label_replace(
        label_replace(
          github_workflow_run_status{job="github-actions-exporter"},
          "organization", "$1", "repo", "(.+)/.+"
        ),
        "repository", "$1", "repo", ".+/(.+)"
      )
    )
    ```

- **Alert on Failed Workflows**:

    Set an alert rule when the threshold is above 0:

    ```promql
    topk by (repo, workflow) (1,
      label_replace(
        label_replace(
          github_workflow_run_status{job="github-actions-exporter", conclusion="failure"},
          "organization", "$1", "repo", "(.+)/.+"
        ),
        "repository", "$1", "repo", ".+/(.+)"
      )
    )
    ```

## Contributing

Contributions are welcome! Please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.