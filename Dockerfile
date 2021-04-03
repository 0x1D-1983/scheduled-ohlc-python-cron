FROM python:3

# Install cron and register crontab
RUN apt-get update && apt-get install -y cron
COPY example-crontab /etc/cron.d/example-crontab
RUN chmod 0644 /etc/cron.d/example-crontab && crontab /etc/cron.d/example-crontab
RUN touch /var/log/cron.log

# Install python packages according to the configuration file requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /usr/src/app
COPY . .

# Start cron job and output lof file content
CMD cron && tail -f /var/log/cron.log