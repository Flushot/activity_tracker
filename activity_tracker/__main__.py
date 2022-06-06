import os
import logging
import threading
import time
import os
from typing import *

import geojson

from . import core, drive

LOG = logging.getLogger(__name__)


def wait_for_watch() -> str:
    """
    Wait for watch to be connected
    :return: Watch USB drive path
    """
    watch_dir = None

    def _is_garmin_watch(base_path: str) -> bool:
        return os.path.exists(os.path.join(base_path, 'GARMIN', 'GarminDevice.xml'))

    def _find_watch_dir(drives: List[drive.Drive]):
        nonlocal watch_dir

        removable_drives = [d for d in drives if d.is_removable]
        # LOG.debug(f'Connected removable drives: {removable_drives}')
        for d in removable_drives:
            base_path = f'{d.letter}\\'
            if _is_garmin_watch(base_path):
                watch_dir = base_path
                break

    _find_watch_dir(drive.DeviceListener.list_drives())
    if watch_dir is None:
        LOG.info(f'Waiting for watch to be connected...')
        listener = drive.DeviceListener(on_change=_find_watch_dir)
        while watch_dir is None:
            listener.poll()
            time.sleep(0.01)

    LOG.info(f'Watch found at {watch_dir}')
    return watch_dir


def main() -> None:
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s | %(thread)-6d | %(levelname)-5s | %(name)s: %(message)s')

    watch_dir = wait_for_watch()

    # with open('locations.json', 'w+') as f:
    #     locations = parse_locations(os.path.join(watch_dir, 'GARMIN', 'ACTIVITY', '*.FIT'))
    #     f.write(geojson.dumps(geojson.LineString([(loc[2], loc[1]) for loc in locations])))

    # Docs: https://dtcooper.github.io/python-fitparse/api.html
    LOG.info('Parsing step data...')
    for steps in core.parse_steps(os.path.join(watch_dir, 'GARMIN', 'MONITOR', '*.FIT')):
        print(f'{steps.timestamp}: Walked {steps.steps:,} steps ({steps.distance_meters / 1000:,.1f} km)')


if __name__ == '__main__':
    main()
