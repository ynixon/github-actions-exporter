# Use the official Python image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /var/log/github-actions/

# Make port 9171 available to the world outside this container
EXPOSE 9171

# Define command to run the exporter
CMD ["python3", "github-actions-exporter.py", "--config-file=github-actions.yml"]