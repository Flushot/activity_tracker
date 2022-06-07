import os
import logging
import threading
import time
import os
from typing import *

import geojson

from . import core, drive

LOG = logging.getLogger(__name__)


def find_watch_dir(wait: bool = True) -> Optional[str]:
    """
    Get path to connected Garmin watch's data files.

    :param wait: If watch isn't connected yet, wait for it to be connected.
    :return: Watch data files path.
    """
    watch_dir = None

    def _is_garmin_watch(base_path: str) -> bool:
        return os.path.exists(os.path.join(base_path, 'GARMIN', 'GarminDevice.xml'))

    def _find_watch_dir(drives: List[drive.Drive]) -> None:
        nonlocal watch_dir

        for d in drives:
            if not d.is_removable:
                continue

            base_path = f'{d.letter}\\'
            if _is_garmin_watch(base_path):
                watch_dir = base_path
                break

    # Watch may already be connected
    _find_watch_dir(drive.DeviceListener.list_drives())

    # Wait for watch to be connected
    if watch_dir is None and wait:
        LOG.info(f'Waiting for watch to be connected...')
        listener = drive.DeviceListener(on_change=_find_watch_dir)
        while watch_dir is None:
            listener.poll()
            time.sleep(0.01)

    if watch_dir is None:
        return

    LOG.info(f'Watch found at {watch_dir}')
    return watch_dir


def main() -> None:
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s | %(thread)-6d | %(levelname)-5s | %(name)s: %(message)s')

    watch_dir = find_watch_dir(wait=True)
    if watch_dir is None:
        LOG.error('Unable to find connected watch')
        return

    # LOG.info('Parsing location data...')
    # with open('locations.json', 'w+') as f:
    #     locations = core.parse_locations(os.path.join(watch_dir, 'GARMIN', 'ACTIVITY', '*.FIT'))
    #     f.write(geojson.dumps(geojson.LineString([(loc.latitude, loc.longitude) for loc in locations])))

    LOG.info('Parsing step data...')
    for steps in core.parse_steps(os.path.join(watch_dir, 'GARMIN', 'MONITOR', '*.FIT')):
        LOG.info(f'{steps.timestamp}: Walked {steps.steps:,} steps ({steps.distance_meters / 1000:,.1f} km)')


if __name__ == '__main__':
    main()
