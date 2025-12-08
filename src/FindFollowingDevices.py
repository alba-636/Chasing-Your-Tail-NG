import sqlite3
import os
import argparse
import json
import time
import statistics
import haversine as hs   
from haversine import Unit
from dataclasses import dataclass
from ConfigHelper import Config, load_config

# Group by nodes of x seconds
NODE_TIME_MAX = 30
NODE_DISTANCE_MAX = 25

@dataclass
class GPSCoordinate():
    latitude: float
    longitude: float

@dataclass
class DeviceCoordinate():
    time: int
    latitude: float
    longitude: float

    def to_gps_coordinate(self) -> GPSCoordinate:
        return GPSCoordinate(self.latitude, self.longitude)
    
    def to_json(self) -> dict:
        return {
            "time": self.time,
            "latitude": self.latitude,
            "longitude": self.longitude
        }

@dataclass
class Device():
    mac: str
    type: str
    coordinates: list[DeviceCoordinate]
    name: str | None

    def to_json(self) -> dict:
        return {
            "mac": self.mac,
            "type": self.type,
            "coordinates": [
                coordinate.to_json() for coordinate in self.coordinates
            ]
        }

def calculate_distance(loc1: GPSCoordinate, loc2: GPSCoordinate) -> float:
    return hs.haversine((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude), unit=Unit.METERS)

@dataclass
class GPSCoordinateNode():
    number: int
    time: int
    gps_coordinate: GPSCoordinate
    devices: list[Device]

    latitudes: list[float]
    lonitudes: list[float]

    def add_device(self, device: Device):
        if next((x for x in self.devices if x.mac == device.mac), None) == None:
            self.devices.append(device)

    def get_avg_coordinate(self) -> GPSCoordinate:
        return GPSCoordinate(
            latitude=statistics.mean(self.latitudes),
            longitude=statistics.mean(self.lonitudes)
        )
    
    def merge(self, node: 'GPSCoordinateNode'):
        for device in node.devices:
            self.add_device(device)

        self.latitudes.extend(node.latitudes)
        self.lonitudes.extend(node.lonitudes)

        self.gps_coordinate = self.get_avg_coordinate()

@dataclass
class Ride():
    start_time: int
    end_time: int
    nodes: list[GPSCoordinateNode]

    def add_node(self, new_node: GPSCoordinateNode):
        if len(self.nodes) == 0:
            self.start_time = new_node.time
        self.end_time = new_node.time

        node = next((node for node in self.nodes if calculate_distance(node.get_avg_coordinate(), new_node.get_avg_coordinate()) < NODE_DISTANCE_MAX), None)
        if node == None:
            self.nodes.append(new_node)
        else:
            node.merge(new_node)

    def get_time(self) -> int:
        return self.nodes[len(self.nodes) - 1].time - self.nodes[0].time

    def get_distance(self) -> float:
        distance = 0
        for i in range(len(self.nodes)):
            if i != len(self.nodes) - 1:
                distance += calculate_distance(
                    self.nodes[i].gps_coordinate,
                    self.nodes[i + 1].gps_coordinate
                )
        return distance

@dataclass
class DeviceDataMap():
    device: Device
    nodes: list[GPSCoordinateNode]

    def get_rides(self) -> list[Ride]:
        if self.get_nodes_length() == 0:
            return []
        return rides_from_nodes(self.nodes)

    def get_nodes_length(self) -> int:
        if self.nodes == None:
            return 0
        return len(self.nodes)
    
    # Return the following time of the device in seconds
    def get_following_time(self) -> int:
        return sum(ride.get_time() for ride in self.get_rides())
    
    # Return the following distance of the device in meters
    def get_following_distance(self) -> float:
        return sum(ride.get_distance() for ride in self.get_rides())
    
    def to_json(self) -> dict:
        return {
            "device": self.device.to_json(),
            "nodes_length": self.get_nodes_length(),
            "following_time": self.get_following_time(),
            "following_distance": self.get_following_distance()
        }

@dataclass
class RidesStatistics():
    rides_length: int
    rides_time: int
    rides_distance: float

    def to_json(self) -> dict:
        return {
            "rides_length": self.rides_length,
            "rides_time": self.rides_time,
            "rides_distance": self.rides_distance
        }

def rides_from_nodes(nodes: list[GPSCoordinateNode]) -> list[Ride]:
    rides:  list[Ride] = []
    last_time: int = 0
    for node in nodes:
        if node.time - last_time > 600: # More than 10 minutes with the last node.
            ride = Ride(node.time, node.time, [node])
            rides.append(ride)
        else:
            rides[len(rides) - 1].add_node(node)
        last_time = node.time
    return rides

class DetectFollowingDevices():
    config: Config
    analyse_full: bool
    only_current: bool

    def __init__(self, config_path, analyse_full: bool, only_current: bool):
        self.config = load_config(config_path)
        self.analyse_full = analyse_full
        self.only_current = only_current

    def get_all_devices_data(self):
        coordinates = []
        try:
            connection = sqlite3.connect(self.config.paths.database)
            cursor = connection.cursor()
            
            if self.analyse_full:
                cursor.execute("""
                    SELECT mac, time, type, latitude, longitude, name
                        FROM devices
                        ORDER BY time;
                """)
            else:
                min_time = time.time() - (self.config.analysis_window_hours * 60 * 60)
                cursor.execute(
                    """
                        SELECT mac, time, type, latitude, longitude, name
                            FROM devices
                            WHERE time > ?
                            ORDER BY time;
                    """,
                    (min_time,)
                )
            
            db_coords = cursor.fetchall()
            connection.close()

            if db_coords:
                coordinates.extend(db_coords)
        except Exception as exception:
            print(f"   ❌ Error reading {os.path.basename(self.config.paths.database)}: {exception}")
        return coordinates

    def build_gps_nodes(self) -> list[GPSCoordinateNode]:
        devices_data = self.get_all_devices_data()

        devices: list[Device] = []
        for data in devices_data:
            device_name: str = data[5]
            device_coordinate = DeviceCoordinate(
                time=int(data[1]),
                latitude=float(data[3]),
                longitude=float(data[4]),
            )

            device = next((device for device in devices if device.mac == data[0]), None)
            if device == None:
                device = Device(
                    mac=data[0],
                    type=data[2],
                    coordinates=[device_coordinate],
                    name=device_name,
                )
                devices.append(device)
            else:
                device.coordinates.append(device_coordinate)
                if device.name == None or device.name == "":
                    device.name = device_name
            
        nodes: list[GPSCoordinateNode] = []
        for device in devices:
            for coordinate in device.coordinates:
                gps_coordinate = GPSCoordinate(coordinate.latitude, coordinate.longitude)
                node = next((node for node in nodes if coordinate.time - node.time < NODE_TIME_MAX), None)
                if node == None:
                    node = GPSCoordinateNode(len(nodes) + 1, coordinate.time, gps_coordinate, [device], [], [])
                    nodes.append(node)
                else:
                    node.add_device(device)
                    node.latitudes.append(gps_coordinate.latitude)
                    node.lonitudes.append(gps_coordinate.longitude)

        return nodes
    
    def load_rides(self, nodes: list[GPSCoordinateNode]) -> list[Ride]:
        if len(nodes) == 0:
            return []
        return rides_from_nodes(nodes)

    def find_followers(self, rides: list[Ride]) -> tuple[list[DeviceDataMap], RidesStatistics]:
        map: list[DeviceDataMap] = []
        for ride in rides:
            for node in ride.nodes:
                for device in node.devices:
                    data = next((x for x in map if x.device.mac == device.mac), None)
                    if data == None:
                        data = DeviceDataMap(device=device, nodes=[node])
                        map.append(data)
                    else:
                        data.nodes.append(node)

        map.sort(key=lambda x: x.get_following_distance(), reverse=True)

        statistics = RidesStatistics(
            rides_length=len(rides),
            rides_time=sum(ride.get_time() for ride in rides),
            rides_distance=sum(ride.get_distance() for ride in rides)
        )

        following_devices: list[DeviceDataMap] = []
        for i in range(len(map)):
            percentage_length = len(map[i].get_rides()) / statistics.rides_length
            percentage_time = map[i].get_following_time() / statistics.rides_time
            percentage_distance = map[i].get_following_distance() / statistics.rides_distance
            if percentage_length > .2 and percentage_time > .2 and percentage_distance > .2:
                following_devices.append(map[i])
        return (following_devices, statistics)

    def start(self):
        nodes = self.build_gps_nodes()
        rides = self.load_rides(nodes)

        following_devices: list[DeviceDataMap] = []
        statistics: RidesStatistics | None = None
        if self.only_current and len(rides) > 0:
            (following_devices, statistics) = self.find_followers([rides[len(rides) - 1]])
        else:
            (following_devices, statistics) = self.find_followers(rides)

        output = { "devices": [device.to_json() for device in following_devices], "statistics": statistics.to_json() }
        print(json.dumps(output))

# TODO: logging
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CYT Detect if a device is following you")

    parser.add_argument("--config-path", type=str, default="config/config.json", help="Path to specific CYT configuration file")
    parser.add_argument("--full", action="store_true", default=False, help="Analyse the all database")
    parser.add_argument("--only-current", action="store_true", default=False, help="Analyse only the current (last) ride")

    args = parser.parse_args()

    detector = DetectFollowingDevices(args.config_path, args.full, args.only_current)
    detector.start()
