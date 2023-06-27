import logging
import os

import pytz
import redis
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import app
from app.api.user.user_service import aggregate_user_login

logger = logging.getLogger()

# Create a scheduler instance
scheduler = BackgroundScheduler()

timezone = pytz.timezone("Asia/Jakarta")
cron_expression = "59 23 * * *"

trigger = CronTrigger.from_crontab(cron_expression, timezone=timezone)
scheduler.add_job(aggregate_user_login, trigger=trigger)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0")
