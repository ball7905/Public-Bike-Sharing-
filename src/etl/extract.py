import logging
import pandas as pd
from config import DATA_DIR

log = logging.getLogger(__name__)


def extract():
    hour = pd.read_csv(DATA_DIR / "hour.csv")
    day = pd.read_csv(DATA_DIR / "day.csv")
    log.info("Extract: hour.csv=%d dòng, day.csv=%d dòng", len(hour), len(day))
    return hour, day
