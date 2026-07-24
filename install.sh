#!/bin/bash

sudo apt update -y
sudo apt install -y python3-pip python3-flask gunicorn curl git

rm -rf /home/ubuntu/app
git clone https://github.com/amrita2201/oaf-workshop-sample-app.git /home/ubuntu/app

cd /home/ubuntu/app

mkdir -p uploads

chown -R ubuntu:ubuntu /home/ubuntu/app

sudo gunicorn --bind 0.0.0.0:80 app:app --daemon
