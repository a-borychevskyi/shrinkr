from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Extract the real client IP address from a request.

    Handles reverse proxy headers (X-Forwarded-For, X-Real-IP) so that the
    correct client IP is returned when the app runs behind an ALB or nginx.
    Falls back to the direct connection address, or "unknown" if unavailable.

    Priority order:
        1. X-Forwarded-For header (first IP in the chain — the original client)
        2. X-Real-IP header
        3. request.client.host (direct TCP connection)
        4. "unknown" (no connection info available)

    Args:
        request: The incoming FastAPI request.

    Returns:
        The client IP address as a string, or "unknown".
    """
    # TODO(andrii): restrict to trusted proxies before production —
    # without a trusted_hosts list, clients can spoof X-Forwarded-For
    # to bypass IP-based rate limiting.
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip

    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"
