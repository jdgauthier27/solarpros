from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "check-pending-email-sends": {
        "task": "solarpros.agents.email_outreach.tasks.process_pending_sends",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "email"},
    },
    "check-pipeline-health": {
        "task": "solarpros.agents.controller.check_pipeline_health",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "orchestration"},
    },
    "daily-trigger-scan": {
        "task": "solarpros.agents.trigger_events.tasks.daily_trigger_scan",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
        "options": {"queue": "trigger_events"},
    },
}
