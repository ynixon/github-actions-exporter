#GitHub Actions Exporter
The GitHub Actions Exporter is a Python script that scrapes data from GitHub Actions workflows and exports the data to a Prometheus endpoint. The data collected includes the number of workflow runs, the average duration of workflow runs, and the status of workflow runs.

##Installation
To install the GitHub Actions Exporter, follow these steps:

To install and run the github-actions-exporter service, you can follow these steps:

Download the github-actions-exporter.tar.gz archive and extract its contents:
```bash
tar -zxvf github-actions-exporter.tar.gz
```
Navigate to the extracted directory:
```bash
cd github-actions-exporter
```
Run the installation script:
```bash
sudo sh install.sh
```
This will copy the necessary files to their appropriate locations, create the github-actions user, and start the github-actions-exporter service.

To verify that the service is running, you can check its status:
```bash
sudo systemctl status github-actions-exporter
```
To stop the service, run:
```bash
sudo systemctl stop github-actions-exporter
```
To disable the service from starting automatically on boot:
```bash
sudo systemctl disable github-actions-exporter
```
To re-enable the service to start automatically on boot:
```bash
sudo systemctl enable github-actions-exporter
```

Clone this repository to your local machine: git clone https://github.com/example/repo.git
Run the installation script as root: sudo ./install.sh
The installation script will copy the necessary files to the correct locations and prompt you to enter your GitHub organization name and access token. The access token must have the necessary permissions to access your organization's workflows.

#Usage
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
##Configuration
The configuration file for the GitHub Actions Exporter is located at /etc/github-actions/github-actions.yml. This file contains the following parameters:

- **org**: Your GitHub organization name
- **token**: Your GitHub access token
- **port**: The port on which the exporter should listen
You can modify these parameters by editing the configuration file and restarting the service:

```bash
sudo systemctl restart github-actions-exporter
```
