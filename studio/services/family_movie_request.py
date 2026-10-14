"""Private family movie request validation."""


def validate_duration(seconds: float) -> bool:
    return 15 <= seconds <= 30
