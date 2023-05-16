import os

import pytz
import redis
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import app
from app.api.user.user_service import aggregate_user_login

listen = ["default"]

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_password = os.getenv("REDIS_PASSWORD", "")

conn = redis.from_url(f"redis://:{redis_password}@{redis_host}:{redis_port}")

# Create a scheduler instance
scheduler = BackgroundScheduler()

timezone = pytz.timezone("Asia/Jakarta")
cron_expression = "59 23 * * *"

trigger = CronTrigger.from_crontab(cron_expression, timezone=timezone)
scheduler.add_job(aggregate_user_login, trigger=trigger)
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
