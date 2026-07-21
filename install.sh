#!/bin/bash
# Update package lists and install required Python packages
sudo apt update -y
sudo apt install -y python3-pip python3-flask gunicorn curl

# Create directory for the application
mkdir -p /home/ubuntu/app
cd /home/ubuntu/app

# Download app.py directly from the GitHub repository main branch
curl -sSL https://raw.githubusercontent.com/Madhuparna04/oaf-workshop-sample-app/main/app.py -o app.py

# Ensure correct ownership
chown -R ubuntu:ubuntu /home/ubuntu/app

# Run app using Gunicorn on Port 80 (accessible by AWS ALB)
sudo gunicorn --bind 0.0.0.0:80 app:app --daemon
