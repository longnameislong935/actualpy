FROM python:3.12-slim-bullseye

# Install system dependencies needed by actualpy
RUN apt-get update && apt-get install -y cron

# Set working directory
WORKDIR /app

# Copy requirements.txt (if you have one)
COPY requirements.txt .
# Install actualpy and other dependencies
RUN pip install --no-cache-dir -r requirements.txt  # Install from requirements.txt
# OR install actualpy directly if you don't use a requirements file:
# RUN pip install --no-cache-dir actualpy

# Copy your script and any other necessary files
COPY massActualCSVImport.py . 
COPY start.sh . 
RUN chmod 0744 /app/massActualCSVImport.py
RUN chmod 0744 /app/start.sh
# COPY transactions.csv . # If your csv is in the same directory.


# Start cron service
#CMD cron && tail -f /var/log/cron.log
ENTRYPOINT ["/bin/sh", "/app/start.sh"]


