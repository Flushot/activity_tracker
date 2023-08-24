import datetime
import glob
from dataclasses import dataclass
import logging
from typing import *

# Docs: https://dtcooper.github.io/python-fitparse/api.html
import fitparse

from . import utils

LOG = logging.getLogger(__name__)


@dataclass
class Location:
    timestamp: datetime.datetime
    latitude: float
    longitude: float
    altitude_meters: float


def parse_locations(file_glob: str) -> List[Location]:
    locations = []

    for file_path in glob.glob(file_glob):
        # LOG.info(f'FILE: {file_path}')
        fitfile = fitparse.FitFile(file_path)

        # Iterate over all messages of type "record"
        # (other types include "device_info", "file_creator", "event", etc)
        for record in fitfile.get_messages('record'):
            lat = record.get_value('position_lat')
            lon = record.get_value('position_long')
            if lat is None or lon is None:
                continue

            lat = utils.semicircles_to_degrees(lat)
            lon = utils.semicircles_to_degrees(lon)

            locations.append(Location(
                timestamp=utils.normalize_ts(record.get_value('timestamp')),
                latitude=lat,
                longitude=lon,
                altitude_meters=record.get_value('altitude')))

    return sorted(locations, key=lambda loc: loc.timestamp)


@dataclass
class Steps:
    timestamp: datetime.datetime
    steps: int
    distance_meters: float


def parse_steps(file_glob: str) -> List[Steps]:
    steps = {}

    for file_path in glob.glob(file_glob):
        # LOG.info(f'FILE: {file_path}')
        fitfile = fitparse.FitFile(file_path)
        last_steps: int = 0
        last_distance: float = 0
        last_ts: Optional[datetime.datetime] = None

        for record in fitfile.get_messages():
            if record.name == 'monitoring_info':
                # utils.print_record(record)
                last_steps = 0
                ts: Optional[datetime.datetime] = record.get_value('timestamp')
                if ts is not None:
                    last_ts = utils.normalize_ts(ts)
                    continue

            if record.name != 'monitoring':
                continue

            activity_type = str(record.get_value('activity_type'))

            if activity_type != 'walking':
                continue

            record_ts = record.get_value('timestamp')
            if record_ts is None:
                record_seconds: int = record.get_value('timestamp_16')
                record_ts = last_ts + datetime.timedelta(seconds=record_seconds)
            else:
                record_ts = utils.normalize_ts(record_ts)

            raw_steps: Optional[int] = record.get_value('steps')
            if raw_steps is None:
                continue

            actual_steps = raw_steps - last_steps
            last_steps = actual_steps

            raw_distance: float = record.get_value('distance')

            actual_distance = raw_distance - last_distance
            last_distance = actual_distance

            # utils.print_record(record)

            if record_ts not in steps:
                steps[record_ts] = Steps(timestamp=record_ts,
                                         steps=actual_steps,
                                         distance_meters=actual_distance)
            else:
                steps[record_ts].steps = actual_steps
                steps[record_ts].distance_meters = actual_distance

    return sorted(steps.values(), key=lambda s: s.timestamp)
