# oaf-workshop-sample-app

Sample Flask app for the OAF workshop, deployed behind an AWS Application Load Balancer (ALB).

## EC2 Launch Template Setup

When creating EC2 instances from a launch template, copy the contents of `install.sh` into the **User data** field. This script installs dependencies, downloads `app.py`, and starts the app with Gunicorn on port 80.

1. Open `install.sh` in this repository.
2. Copy the entire script.
3. In the AWS EC2 console, edit your launch template (or create a new version).
4. Under **Advanced details**, paste the script into **User data**.
5. Launch or refresh instances from that template version.

## Load Testing

After the ALB and EC2 instances are running, run the load test from a machine with Python 3 and the `requests` library installed:

```bash
python3 load_test.py http://test-alb-2031674237.us-east-1.elb.amazonaws.com/
```

Replace the URL with your ALB DNS name if it differs. The script sends concurrent GET requests to the load balancer and prints a summary of responses
