# Platform adapters for blog scraping.
# Showit sites use Jetpack/WordPress backend — route through WordPressAdapter.
# Supported: WordPress (REST API + HTML fallback), Squarespace (sitemap + HTML), Generic (trafilatura).

from .wordpress import WordPressAdapter
from .squarespace import SquarespaceAdapter
from .generic import GenericAdapter

__all__ = ["WordPressAdapter", "SquarespaceAdapter", "GenericAdapter"]
