"""
Dependency Injection container.

Wires abstract ports → concrete adapters. To swap a provider
(e.g., OpenAI → Ollama), change the adapter instantiation here.
Nothing else in the codebase changes  (Open/Closed Principle).
"""

from functools import lru_cache

from fastapi import Depends
from supabase import create_client

from app.adapters.document_adapter import DocumentAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.openai_embedding import OpenAIEmbeddingAdapter
from app.adapters.supabase_adapter import SupabaseAdapter
from app.adapters.supabase_storage_adapter import SupabaseStorageAdapter
from app.config import settings
from app.ports.ai_port import AIPort
from app.ports.database_port import DatabasePort
from app.ports.document_port import DocumentPort
from app.ports.embedding_port import EmbeddingPort
from app.ports.storage_port import StoragePort


# ── Singletons (cached) ──────────────────────────────────────


@lru_cache(maxsize=1)
def _get_supabase_client():
    # Use service role key — bypasses RLS for server-side operations
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


@lru_cache(maxsize=1)
def _get_openai_adapter() -> OpenAIAdapter:
    return OpenAIAdapter(api_key=settings.openai_api_key)


@lru_cache(maxsize=1)
def _get_embedding_adapter() -> OpenAIEmbeddingAdapter:
    return OpenAIEmbeddingAdapter(api_key=settings.openai_api_key)


@lru_cache(maxsize=1)
def _get_supabase_adapter() -> SupabaseAdapter:
    return SupabaseAdapter(client=_get_supabase_client())


@lru_cache(maxsize=1)
def _get_storage_adapter() -> SupabaseStorageAdapter:
    return SupabaseStorageAdapter(client=_get_supabase_client())


@lru_cache(maxsize=1)
def _get_document_adapter() -> DocumentAdapter:
    return DocumentAdapter()


# ── FastAPI Dependencies (return abstract types) ──────────────


def get_ai_service() -> AIPort:
    """Inject the AI adapter."""
    return _get_openai_adapter()


def get_embedding_service() -> EmbeddingPort:
    """Inject the embedding adapter."""
    return _get_embedding_adapter()


def get_db() -> DatabasePort:
    """Inject the database adapter."""
    return _get_supabase_adapter()


def get_storage() -> StoragePort:
    """Inject the file storage adapter."""
    return _get_storage_adapter()


def get_document_parser() -> DocumentPort:
    """Inject the document text extractor (PDF + DOCX)."""
    return _get_document_adapter()


# ── Scraper Registry ──────────────────────────────────────────

from app.scraper.scraper_port import ScraperPort  # noqa: E402
from app.scraper.deloitte_adapter import DeloitteAdapter  # noqa: E402
from app.scraper.pwc_adapter import PwCAdapter  # noqa: E402
from app.scraper.kpmg_adapter import KPMGAdapter  # noqa: E402
from app.scraper.ey_adapter import EYAdapter  # noqa: E402

_SCRAPER_REGISTRY: dict[str, type[ScraperPort]] = {
    "deloitte": DeloitteAdapter,
    "pwc": PwCAdapter,
    "kpmg": KPMGAdapter,
    "ey": EYAdapter,
}


def get_scraper(source_name: str) -> ScraperPort:
    """Resolve a source name to its scraper adapter instance."""
    cls = _SCRAPER_REGISTRY.get(source_name.lower())
    if not cls:
        raise ValueError(
            f"Unknown source: {source_name}. "
            f"Available: {', '.join(_SCRAPER_REGISTRY.keys())}"
        )
    return cls()


def get_all_scrapers() -> list[ScraperPort]:
    """Returns a list of all registered scraper instances."""
    return [cls() for cls in _SCRAPER_REGISTRY.values()]


# ── Domain Services ───────────────────────────────────────────

from app.services.matching_service import MatchingService  # noqa: E402


def get_matching_service(
    db: DatabasePort = Depends(get_db), ai: AIPort = Depends(get_ai_service)
) -> MatchingService:
    """Injects DB and AI adapters into the matching domain service."""
    return MatchingService(db=db, ai=ai)


from app.services.analytics_service import AnalyticsService

def get_analytics_service(db: DatabasePort = Depends(get_db)) -> AnalyticsService:
    """Injects DB adapter into analytics service."""
    return AnalyticsService(db=db)
