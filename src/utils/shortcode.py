"""Short-code generation for URL shortener links.

Codes are 7 base62 characters by default, which gives 62^7 ≈ 3.5 * 10^12
distinct codes. That's enough that random generation with a simple
"insert-and-retry-on-conflict" strategy stays collision-free in practice
without a central counter or coordinator.
"""

from secrets import choice

ALPHABET: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
DEFAULT_LENGTH: int = 7


def generate_short_code(length: int = DEFAULT_LENGTH) -> str:
    """Return a cryptographically-random base62 short code.

    Uses :func:`secrets.choice` so codes are unpredictable (important when
    IDs are the only thing gating access to a link). Collisions are
    handled at the persistence layer via the unique constraint + retry.
    """
    if length <= 0:
        raise ValueError("length must be positive")
    return "".join(choice(ALPHABET) for _ in range(length))
