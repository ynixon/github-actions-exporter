#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root"
  exit 1
fi

# Define variables
BIN_PATH="/usr/local/bin"
ETC_PATH="/etc/github-actions"
ORG=""
TOKEN=""
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $SCRIPT_DIR

# ask for ORG and TOKEN if not provided as arguments
if [ $# -lt 2 ]; then
    read -p "Enter your Github ORG: " ORG
    read -p "Enter your Github TOKEN: " TOKEN
else
    ORG=$1
    TOKEN=$2
fi

# Copy github-actions-exporter.py to BIN_PATH
cp github-actions-exporter.py $BIN_PATH

# Copy github-actions.yml to ETC_PATH and replace ORG and TOKEN
if [ ! -d $ETC_PATH ]
then
  mkdir -p $ETC_PATH
fi
cp github-actions.yml $ETC_PATH
sed -i "s/<ORG>/$ORG/g" $ETC_PATH/github-actions.yml
sed -i "s/<TOKEN>/$TOKEN/g" $ETC_PATH/github-actions.yml

# Copy github-actions-exporter.service to /etc/systemd/system
cp github-actions-exporter.service /etc/systemd/system

# Create user and group github-actions
groupadd github-actions
useradd -r -g github-actions -s /sbin/nologin github-actions

# Change ownership of the files
chown -R github-actions:github-actions $BIN_PATH/github-actions-exporter.py
chown -R github-actions:github-actions $ETC_PATH/github-actions.yml
chown -R github-actions:github-actions /etc/systemd/system/github-actions-exporter.service

# Reload systemctl daemon
systemctl daemon-reload

# Enable and start the service
systemctl enable github-actions-exporter

pip3 install -r requirments.txt

systemctl start github-actions-exporter

echo "Installation complete."

