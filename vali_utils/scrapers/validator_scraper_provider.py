import threading
from typing import Callable, Dict
from common.data import DataSource
from scraping.reddit.reddit_lite_scraper import RedditLiteScraper
from scraping.reddit.reddit_custom_scraper import RedditCustomScraper
from scraping.scraper import Scraper, ScraperId
from scraping.x.microworlds_scraper import MicroworldsTwitterScraper
from scraping.x.apidojo_scraper import ApiDojoTwitterScraper
from scraping.x.quacker_url_scraper import QuackerUrlScraper
from scraping.youtube.youtube_custom_scraper import YouTubeTranscriptScraper
from scraping.youtube.invideoiq_transcript_scraper import YouTubeChannelTranscriptScraper

from vali_utils.scrapers.szill_zillow_scraper import SzillZillowScraper

# Validator scraper factories include both RapidAPI and Szill options
VALIDATOR_SCRAPER_FACTORIES = {
    ScraperId.REDDIT_LITE: RedditLiteScraper,
    # For backwards compatibility with old configs, remap x.flash to x.apidojo.
    ScraperId.X_FLASH: MicroworldsTwitterScraper,
    ScraperId.REDDIT_CUSTOM: RedditCustomScraper,
    ScraperId.X_MICROWORLDS: MicroworldsTwitterScraper,
    ScraperId.X_APIDOJO: ApiDojoTwitterScraper,
    ScraperId.X_QUACKER: QuackerUrlScraper,
    ScraperId.YOUTUBE_CUSTOM_TRANSCRIPT: YouTubeTranscriptScraper,
    ScraperId.YOUTUBE_APIFY_TRANSCRIPT: YouTubeChannelTranscriptScraper,
}

class ValidatorScraperId:
    """Extended scraper IDs for validators"""
    SZILL_ZILLOW = "Szill.zillow"


class ValidatorScraperProvider:
    """Scraper provider for validators."""

    def __init__(
        self, 
        factories: Dict[str, Callable[[], Scraper]] = None
    ):
        self.factories = factories or VALIDATOR_SCRAPER_FACTORIES.copy()
        
        self.factories[ValidatorScraperId.SZILL_ZILLOW] = SzillZillowScraper

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
            ScraperId.REDDIT_LITE: "Reddit Lite Scraper",
            ScraperId.REDDIT_CUSTOM: "Reddit Custom Scraper", 
            ScraperId.X_MICROWORLDS: "Twitter/X Microworlds Scraper",
            ScraperId.X_APIDOJO: "Twitter/X ApiDojo Scraper",
            ScraperId.X_QUACKER: "Twitter/X Quacker URL Scraper",
            ScraperId.YOUTUBE_CUSTOM_TRANSCRIPT: "YouTube Custom Transcript Scraper",
            ScraperId.YOUTUBE_APIFY_TRANSCRIPT: "YouTube Apify Transcript Scraper",
                                      ValidatorScraperId.SZILL_ZILLOW: "Szill Scraper"
        }

 