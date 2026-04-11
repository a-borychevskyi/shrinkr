# API Reference

Shrinkr exposes a REST API versioned under `/api/v0/`.  Interactive documentation
is available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the server is running.

## Links

### Create a short link

```
POST /api/v0/shortener/url
```

**Request body**

| Field          | Type     | Required | Description                     |
|----------------|----------|----------|---------------------------------|
| `original_url` | `string` | yes      | The URL to shorten              |
| `custom_alias` | `string` | no       | Custom short code               |
| `expires_at`   | `string` | no       | ISO-8601 expiration timestamp   |

**Response** `201 Created`

```json
{
  "status": "success",
  "payload": {
    "id": 1,
    "short_code": "abc123",
    "original_url": "https://example.com",
    "is_active": true,
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

### Redirect

```
GET /{short_code}
```

Returns a `301 Moved Permanently` redirect to the original URL and records the click.

### Get link details

```
GET /api/v0/shortener/url/{short_code}
```

### Deactivate a link

```
PATCH /api/v0/shortener/url/{short_code}/deactivate
```

### Delete a link

```
DELETE /api/v0/shortener/url/{short_code}
```

## Analytics

### Get click stats

```
GET /api/v0/shortener/url/{short_code}/stats
```

Returns total clicks and per-click metadata (timestamp, referrer, user-agent, IP).

## System

| Endpoint    | Description                              |
|-------------|------------------------------------------|
| `GET /health` | Liveness probe — always returns `200`  |
| `GET /ready`  | Readiness probe — checks DB and Redis  |
| `GET /metrics` | Prometheus-format metrics              |

## Error Format

All errors follow a consistent structure:

```json
{
  "status": "error",
  "error": {
    "code": "NOT_FOUND",
    "message": "Link not found"
  }
}
```

## Rate Limiting

Link creation is rate-limited per IP.  When the limit is exceeded the API returns
`429 Too Many Requests` with `Retry-After`, `X-RateLimit-Limit`, and
`X-RateLimit-Remaining` headers.
