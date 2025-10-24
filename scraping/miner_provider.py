from typing import Callable, Dict
from common.data import DataSource
from scraping.scraper import Scraper, ScraperId

MINER_SCRAPER_FACTORIES = {}


class MinerScraperProvider:
    """Scraper provider for miners."""

    def __init__(
        self, factories: Dict[DataSource, Callable[[], Scraper]] = MINER_SCRAPER_FACTORIES
    ):
        self.factories = factories

    def get(self, scraper_id: ScraperId) -> Scraper:
        """Returns a scraper for the given scraper id."""

        # TODO: Add a check to see if the scraper is supported for miners.

        assert scraper_id in self.factories, f"Scraper id {scraper_id} not supported for miners."

        return self.factories[scraper_id]() 