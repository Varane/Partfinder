import logging

from .normalize import normalize_item
from .db import init_db, upsert_part
from .scrapers import AutopliusScraper, MLAutoScraper, MobileDeScraper, RRRScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_all_scrapers() -> None:
    scrapers = [RRRScraper(), MLAutoScraper(), AutopliusScraper(), MobileDeScraper()]
    inserted = 0
    updated = 0

    for scraper in scrapers:
        logger.info("Running scraper for %s", scraper.platform)
        raw_items = scraper.fetch_all()
        logger.info("%s returned %s items", scraper.platform, len(raw_items))
        for raw in raw_items:
            item = normalize_item(raw)
            if upsert_part(item):
                inserted += 1
            else:
                updated += 1

    logger.info("Inserted %s items, updated %s items", inserted, updated)


def main() -> None:
    init_db()
    run_all_scrapers()


if __name__ == "__main__":
    main()
