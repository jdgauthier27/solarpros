from celery import Celery

from solarpros.config import settings


def create_celery_app() -> Celery:
    app = Celery("solarpros")

    app.conf.update(
        broker_url=settings.celery_broker_url,
        result_backend=settings.celery_result_backend,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="America/Los_Angeles",
        enable_utc=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_track_started=True,
        result_expires=86400,  # 24 hours
    )

    # Queue routing
    app.conf.task_routes = {
        "solarpros.agents.property_discovery.tasks.*": {"queue": "scraping"},
        "solarpros.agents.solar_analysis.tasks.*": {"queue": "solar_api"},
        "solarpros.agents.owner_id.tasks.*": {"queue": "owner_lookup"},
        "solarpros.agents.scoring.tasks.*": {"queue": "scoring"},
        "solarpros.agents.email_outreach.tasks.*": {"queue": "email"},
        "solarpros.agents.controller.*": {"queue": "orchestration"},
    }

    # Rate limits per task
    app.conf.task_annotations = {
        "solarpros.agents.property_discovery.tasks.*": {
            "rate_limit": f"{settings.scraping_rate_per_minute}/m",
        },
        "solarpros.agents.solar_analysis.tasks.*": {
            "rate_limit": f"{settings.solar_api_rate_per_minute}/m",
        },
        "solarpros.agents.owner_id.tasks.*": {
            "rate_limit": f"{settings.owner_lookup_rate_per_minute}/m",
        },
        "solarpros.agents.email_outreach.tasks.*": {
            "rate_limit": f"{settings.email_rate_per_hour}/h",
        },
    }

    # Default retry policy
    app.conf.task_default_retry_delay = 60
    app.conf.task_max_retries = 5

    # Auto-discover tasks
    app.autodiscover_tasks(
        [
            "solarpros.agents.property_discovery",
            "solarpros.agents.solar_analysis",
            "solarpros.agents.owner_id",
            "solarpros.agents.scoring",
            "solarpros.agents.email_outreach",
            "solarpros.agents.controller",
        ]
    )

    return app


celery_app = create_celery_app()
