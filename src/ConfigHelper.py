from typing import List
from typing import Any
from dataclasses import dataclass
import json

@dataclass
class IgnoreLists:
    mac: str
    ssid: str

    @staticmethod
    def from_dict(obj: Any) -> 'IgnoreLists':
        _mac = str(obj.get("mac"))
        _ssid = str(obj.get("ssid"))
        return IgnoreLists(_mac, _ssid)

@dataclass
class Paths:
    log_dir: str
    kismet_logs: str
    ignore_lists: IgnoreLists

    @staticmethod
    def from_dict(obj: Any) -> 'Paths':
        _log_dir = str(obj.get("log_dir"))
        _kismet_logs = str(obj.get("kismet_logs"))
        _ignore_lists = IgnoreLists.from_dict(obj.get("ignore_lists"))
        return Paths(_log_dir, _kismet_logs, _ignore_lists)

@dataclass
class Search:
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    @staticmethod
    def from_dict(obj: Any) -> 'Search':
        _lat_min = float(obj.get("lat_min"))
        _lat_max = float(obj.get("lat_max"))
        _lon_min = float(obj.get("lon_min"))
        _lon_max = float(obj.get("lon_max"))
        return Search(_lat_min, _lat_max, _lon_min, _lon_max)

@dataclass
class TimeWindows:
    recent: int
    medium: int
    old: int
    oldest: int

    @staticmethod
    def from_dict(obj: Any) -> 'TimeWindows':
        _recent = int(obj.get("recent"))
        _medium = int(obj.get("medium"))
        _old = int(obj.get("old"))
        _oldest = int(obj.get("oldest"))
        return TimeWindows(_recent, _medium, _old, _oldest)

@dataclass
class Timing:
    check_interval: int
    list_update_interval: int
    time_windows: TimeWindows

    @staticmethod
    def from_dict(obj: Any) -> 'Timing':
        _check_interval = int(obj.get("check_interval"))
        _list_update_interval = int(obj.get("list_update_interval"))
        _time_windows = TimeWindows.from_dict(obj.get("time_windows"))
        return Timing(_check_interval, _list_update_interval, _time_windows)

@dataclass
class DetectorThresholds:
    min_appearances: int
    min_time_span_hours: float
    min_persistence_score: float

    @staticmethod
    def from_dict(obj: Any) -> 'DetectorThresholds':
        _min_appearances = int(obj.get("min_appearances"))
        _min_time_span_hours = float(obj.get("min_time_span_hours"))
        _min_persistence_score = float(obj.get("min_persistence_score"))
        return DetectorThresholds(_min_appearances, _min_time_span_hours, _min_persistence_score)

@dataclass
class GPSTracker:
    location_threshold: int
    session_timeout: int

    @staticmethod
    def from_dict(obj: Any) -> 'GPSTracker':
        _location_threshold = int(obj.get("location_threshold"))
        _session_timeout = int(obj.get("session_timeout"))
        return GPSTracker(_location_threshold, _session_timeout)
    
@dataclass
class Kismet:
    username: str
    password: str
    url: str
    port: int

    @staticmethod
    def from_dict(obj: Any) -> 'Kismet':
        _username = str(obj.get("username"))
        _password = str(obj.get("password"))
        _url = str(obj.get("url"))
        _port = int(obj.get("port"))
        return Kismet(_username, _password, _url, _port)
    
@dataclass
class Telegram:
    bot_token: str
    chat_id: str

    @staticmethod
    def from_dict(obj: Any) -> 'Telegram':
        _bot_token = str(obj.get("bot_token"))
        _chat_id = str(obj.get("chat_id"))
        return Telegram(_bot_token, _chat_id)

@dataclass
class Config:
    analysis_window_hours: int
    paths: Paths
    timing: Timing
    search: Search
    detector_thresholds: DetectorThresholds
    gps_tracker: GPSTracker
    kismet: Kismet
    telegram: Telegram

    @staticmethod
    def from_dict(obj: Any) -> 'Config':
        _analysis_window_hours = int(obj.get("analysis_window_hours"))
        _paths = Paths.from_dict(obj.get("paths"))
        _timing = Timing.from_dict(obj.get("timing"))
        _search = Search.from_dict(obj.get("search"))
        _detector_thresholds = DetectorThresholds.from_dict(obj.get("detector_thresholds"))
        _gps_tracker = GPSTracker.from_dict(obj.get("gps_tracker"))
        _kismet = Kismet.from_dict(obj.get("kismet"))
        _telegram = Telegram.from_dict(obj.get("telegram"))
        return Config(_analysis_window_hours, _paths, _timing, _search, _detector_thresholds, _gps_tracker, _kismet, _telegram)

def load_config(config_path: str) -> Config:
    with open(config_path, 'r') as config_file:
        config_string = json.load(config_file)
        config = Config.from_dict(config_string)

        return config
