from typing import Callable, Dict
from scraping.scraper import Scraper, ScraperId

from vali_utils.scrapers.szill_zillow_scraper import SzillZillowScraper

VALIDATOR_SCRAPER_FACTORIES = {}

class ValidatorScraperId:
    """Extended scraper IDs for validators"""
    SZILL_ZILLOW = "Szill.zillow"


class ValidatorScraperProvider:
    """Scraper provider for validators."""

    def __init__(
        self, 
        factories: Dict[str, Callable[[], Scraper]] = None,
        proxy_url: str = None,
        use_scrapingbee: bool = False,
        max_concurrent: int = 1
    ):
        self.factories = factories or VALIDATOR_SCRAPER_FACTORIES.copy()
        self.proxy_url = proxy_url
        self.use_scrapingbee = use_scrapingbee
        self.max_concurrent = max_concurrent
        
        # Create factory function that passes configuration
        # Reduce concurrent requests to 1 for better success rate with Zillow
        safe_concurrent = min(self.max_concurrent, 1)
        self.factories[ValidatorScraperId.SZILL_ZILLOW] = lambda: SzillZillowScraper(
            proxy_url=self.proxy_url,
            use_scrapingbee=self.use_scrapingbee,
            max_concurrent=safe_concurrent
        )

    def get(self, scraper_id: str) -> Scraper:
        """Returns a scraper for the given scraper id."""
        
        # Map custom zillow scraper ID to Szill implementation
        if scraper_id == "Szill.zillow":
            scraper_id = ValidatorScraperId.SZILL_ZILLOW

        assert scraper_id in self.factories, f"Scraper id {scraper_id} not supported for validators."

        return self.factories[scraper_id]()

    def get_available_scrapers(self) -> Dict[str, str]:
        """Returns a mapping of available scraper IDs to their descriptions"""
        return {
            ValidatorScraperId.SZILL_ZILLOW: "Szill Zillow Scraper"
        }

 