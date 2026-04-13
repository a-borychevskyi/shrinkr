from typing import Annotated

from fastapi import APIRouter, Request
from fastapi.params import Depends
from fastapi.responses import RedirectResponse
from opentelemetry import trace

from src.di.repositories.url import get_url_cache_repository
from src.di.services.url import get_url_service
from src.orm.filters.url import UrlFilter
from src.repositories.url import UrlCacheRepository
from src.services.click_ingest import ClickEvent
from src.services.database.url import UrlService

router = APIRouter(tags=["Redirect"])

tracer = trace.get_tracer(__name__)


@router.get(
    "/{short_code}",
    response_model=None,
    status_code=302,
)
async def redirect_to_url(
    short_code: str,
    request: Request,
    url_service: Annotated[UrlService, Depends(get_url_service)],
    url_cache_repository: Annotated[
        UrlCacheRepository, Depends(get_url_cache_repository)
    ],
) -> RedirectResponse:
    span = trace.get_current_span()
    span.set_attribute("url.short_code", short_code)

    response = await url_cache_repository.get_by_short_code(short_code)
    cache_hit = response is not None
    if not cache_hit:
        filters = UrlFilter(short_code=short_code)
        response = await url_service.get_one(filters)
        await url_cache_repository.set_short_code(short_code, response)

    span.set_attribute("cache.hit", cache_hit)

    if response is None:
        span.set_attribute("url.found", False)
        return RedirectResponse(url="/", status_code=302)

    span.set_attribute("url.found", True)
    span.set_attribute("url.target_url", response.target_url)

    _id = response.id if response.id is not None else -1
    ip_address = request.client.host if request.client is not None else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    request.app.state.click_ingester.enqueue(
        ClickEvent(url_id=_id, user_agent=user_agent, ip_address=ip_address)
    )
    return RedirectResponse(url=response.target_url, status_code=302)
