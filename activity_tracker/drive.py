# Source: https://abdus.dev/posts/python-monitor-usb/
import logging
from dataclasses import dataclass
from typing import *
import win32api
import win32con
import win32gui
import ctypes
from ctypes import wintypes
import string


@dataclass
class Drive:
    DRIVE_TYPES: ClassVar[Dict[int, str]] = {
        0: 'Unknown',
        1: 'No Root Directory',
        2: 'Removable Disk',
        3: 'Local Disk',
        4: 'Network Drive',
        5: 'Compact Disc',
        6: 'RAM Disk',
    }

    letter: str
    label: str
    drive_type: int

    @property
    def is_removable(self) -> bool:
        return self.drive_type == 2

    @property
    def drive_type_name(self) -> str:
        return self.DRIVE_TYPES[self.drive_type]


class DeviceListener:
    """
    Listens to Win32 `WM_DEVICECHANGE` messages
    and trigger a callback when a device has been plugged in or out

    See: https://docs.microsoft.com/en-us/windows/win32/devio/wm-devicechange
    """
    WM_DEVICECHANGE_EVENTS: Dict[int, Tuple[str, str]] = {
        0x0019: ('DBT_CONFIGCHANGECANCELED',
                 'A request to change the current configuration (dock or undock) has been canceled.'),
        0x0018: ('DBT_CONFIGCHANGED',
                 'The current configuration has changed, due to a dock or undock.'),
        0x8006: ('DBT_CUSTOMEVENT',
                 'A custom event has occurred.'),
        0x8000: ('DBT_DEVICEARRIVAL',
                 'A device or piece of media has been inserted and is now available.'),
        0x8001: ('DBT_DEVICEQUERYREMOVE',
                 'Permission is requested to remove a device or piece of media. '
                 'Any application can deny this request and cancel the removal.'),
        0x8002: ('DBT_DEVICEQUERYREMOVEFAILED',
                 'A request to remove a device or piece of media has been canceled.'),
        0x8004: ('DBT_DEVICEREMOVECOMPLETE',
                 'A device or piece of media has been removed.'),
        0x8003: ('DBT_DEVICEREMOVEPENDING',
                 'A device or piece of media is about to be removed. Cannot be denied.'),
        0x8005: ('DBT_DEVICETYPESPECIFIC',
                 'A device-specific event has occurred.'),
        0x0007: ('DBT_DEVNODES_CHANGED',
                 'A device has been added to or removed from the system.'),
        0x0017: ('DBT_QUERYCHANGECONFIG',
                 'Permission is requested to change the current configuration (dock or undock).'),
        0xFFFF: ('DBT_USERDEFINED',
                 'The meaning of this message is user-defined.'),
    }

    log: logging.Logger = logging.getLogger(__name__ + '.' + __qualname__)
    on_change: Callable[[List[Drive]], None]

    def __init__(self, on_change: Callable[[List[Drive]], None]):
        self.on_change = on_change
        self._create_window()

    def start(self) -> None:
        self.log.debug(f'Listening to messages...')
        win32gui.PumpMessages()

    def poll(self) -> None:
        win32gui.PumpWaitingMessages()

    def _create_window(self) -> int:
        """
        Create a window for listening to messages
        https://docs.microsoft.com/en-us/windows/win32/learnwin32/creating-a-window#creating-the-window

        See also: https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createwindoww

        :return: window handle
        """
        self.log.debug(f'Creating window to listen for drive changes...')
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._on_message
        wc.lpszClassName = self.__class__.__name__
        wc.hInstance = win32api.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        hwnd = win32gui.CreateWindow(class_atom, self.__class__.__name__, 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)
        self.log.debug(f'Created listener window {hwnd:x}')
        return hwnd

    def _on_message(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg != win32con.WM_DEVICECHANGE:
            return 0

        event, description = self.WM_DEVICECHANGE_EVENTS[wparam]

        if event == 'DBT_DEVICEARRIVAL':
            self.log.debug('A device has been plugged in')
            self.on_change(self.list_drives())
        elif event == 'DBT_DEVICEREMOVECOMPLETE':
            self.log.debug('A device has been removed')
            self.on_change(self.list_drives())
        else:
            self.log.debug(f'Received message: {event} = {description}')

        return 0

    @classmethod
    def list_drives(cls) -> List[Drive]:
        """
        Get a list of drives using WMI

        :return: list of drives
        """
        drive_bits = ctypes.windll.kernel32.GetLogicalDrives()
        drive_letters = [letter for i, letter in enumerate(string.ascii_uppercase) if drive_bits >> i & 1 == 1]

        drives = []
        for drive_letter in drive_letters:
            volume_name = ctypes.create_unicode_buffer(wintypes.MAX_PATH + 1)
            ctypes.windll.kernel32.GetVolumeInformationW(f'{drive_letter}:\\',
                                                         volume_name, ctypes.sizeof(volume_name),
                                                         None, None, None, None, 0)
            drives.append(Drive(letter=f'{drive_letter}:',
                                label=volume_name.value,
                                drive_type=ctypes.windll.kernel32.GetDriveTypeW(f'{drive_letter}:\\')))

        return drives
