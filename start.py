import subprocess

#subprocess.run("uvicorn app:app --host localhost --port 443 --ssl-certfile=/Users/Alex/localhost.pem --ssl-keyfile=/Users/Alex/localhost.key", shell=True)
subprocess.run("/home/ubuntu/calendar-agent/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 80", shell=True)