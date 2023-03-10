# GitHub Actions Exporter
The GitHub Actions Exporter is a Python script that scrapes data from GitHub Actions workflows and exports the data to a Prometheus endpoint. The data collected includes the number of workflow runs, the average duration of workflow runs, and the status of workflow runs.

## Installation
To install the GitHub Actions Exporter, follow these steps:

Clone this repository to your local machine:

bash
```bash
git clone https://github.com/ynixon/github-actions-exporter.git
```
Navigate to the cloned repository:

```bash
cd github-actions-exporter
```
Run the installation script as root:

```bash
sudo ./install.sh
```
The installation script will copy the necessary files to the correct locations and prompt you to enter your GitHub organization name and access token. The access token must have the necessary permissions to access your organization's workflows.

## Usage
Once the installation is complete, you can start the GitHub Actions Exporter service by running:

```bash
sudo systemctl start github-actions-exporter
```
To enable the service to start on boot, run:

```bash
sudo systemctl enable github-actions-exporter
```
By default, the service listens on port 9171. You can change this port by modifying the port parameter in /etc/github-actions/github-actions.yml.

To verify that the exporter is running, you can visit http://localhost:9171/metrics in a web browser or use the curl command:
```bash
curl http://localhost:9171/metrics
```

## Configuration
The configuration file for the GitHub Actions Exporter is located at /etc/github-actions/github-actions.yml. This file contains the following parameters:

- **org**: Your GitHub organization name
- **token**: Your GitHub access token
- **port**: The port on which the exporter should listen
You can modify these parameters by editing the configuration file and restarting the service:
```bash
sudo systemctl restart github-actions-exporter
```

## Dashboard
The GitHub Actions Exporter comes with a pre-configured dashboard JSON file called Dashboard-GitHub-Actions-Workflows.json. This file can be imported into a Grafana instance to display the data collected by the exporter in a visual format. To import the dashboard, follow these steps:

1. Open your Grafana instance and navigate to the Dashboards section.
1. Click on the Import button and select Upload .json File.
1. Select the Dashboard-GitHub-Actions-Workflows.json file and click on Import.

Once imported, you can view and customize the dashboard to suit your needs.
