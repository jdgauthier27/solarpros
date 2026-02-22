from kombu import Exchange, Queue

# Define exchanges
default_exchange = Exchange("default", type="direct")
dead_letter_exchange = Exchange("dead_letter", type="direct")

# Define queues
CELERY_QUEUES = (
    Queue("scraping", default_exchange, routing_key="scraping"),
    Queue("solar_api", default_exchange, routing_key="solar_api"),
    Queue("owner_lookup", default_exchange, routing_key="owner_lookup"),
    Queue("enrichment", default_exchange, routing_key="enrichment"),
    Queue("trigger_events", default_exchange, routing_key="trigger_events"),
    Queue("scoring", default_exchange, routing_key="scoring"),
    Queue("email", default_exchange, routing_key="email"),
    Queue("orchestration", default_exchange, routing_key="orchestration"),
    Queue("takeoff", default_exchange, routing_key="takeoff"),
    Queue(
        "dead_letter",
        dead_letter_exchange,
        routing_key="dead_letter",
    ),
)
