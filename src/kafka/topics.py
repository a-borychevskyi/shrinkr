"""Kafka topic constants.

Centralised so both the producer (API) and consumer (worker) reference
the same names. Partition count is also recorded here for documentation
and for the local-dev topic auto-create config.
"""

CLICKS_TOPIC = "clicks"
CLICKS_PARTITIONS = 3
