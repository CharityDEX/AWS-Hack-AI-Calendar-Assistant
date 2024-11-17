import subprocess

subprocess.run("uvicorn app:app --host localhost --port 443 --ssl-certfile=/Users/Alex/localhost.pem --ssl-keyfile=/Users/Alex/localhost.key", shell=True)