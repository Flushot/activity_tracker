import datetime
import logging
from typing import *

import pytz
import fitparse

LOG = logging.getLogger(__name__)


def print_record(record: fitparse.DataMessage) -> None:
    # Records can contain multiple pieces of data (ex: timestamp, latitude, longitude, etc)
    for data in record:
        # Print the name and value of the data (and the units if it has any)
        if data.units:
            print(" * {}: {} ({})".format(data.name, data.value, data.units))
        else:
            print(" * {}: {}".format(data.name, data.value))

    print("---")


def semicircles_to_degrees(semicircles: Optional[int]) -> Optional[float]:
    if semicircles is not None:
        return semicircles * (180 / 2**31)


def normalize_ts(ts: datetime.datetime) -> datetime.datetime:
    return ts.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('America/Los_Angeles'))
