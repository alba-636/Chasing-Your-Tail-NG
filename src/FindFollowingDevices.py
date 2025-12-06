import sqlite3
import os
import argparse
import haversine as hs   
from haversine import Unit

from dataclasses import dataclass
from ConfigHelper import Config, load_config

# Group by nodes of x seconds
NODE_TIME_MAX = 60

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

@dataclass
class Device():
    mac: str
    type: str
    coordinates: list[DeviceCoordinate]
    name: str | None

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

@dataclass
class Ride():
    start_time: int
    end_time: int
    nodes: list[GPSCoordinateNode]

    def add_node(self, node: GPSCoordinateNode):
        if len(self.nodes) == 0:
            self.start_time = node.time
        self.end_time = node.time
        self.nodes.append(node)

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
        return rides_from_nodes(self.nodes)

    def get_nodes_length(self) -> int:
        if self.nodes == None:
            return 0
        return sum(len(ride.nodes) for ride in self.get_rides())
    
    def get_following_time(self) -> int:
        if self.get_nodes_length() == 0:
            return 0
        return sum(ride.get_time() for ride in self.get_rides())
    
    def get_following_distance(self) -> float:
        return sum(ride.get_distance() for ride in self.get_rides())

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
    rides: list[Ride] = []

    def __init__(self, config_path):
        self.config = load_config(config_path)

    def get_all_devices_data(self):
        coordinates = []
        try:
            connection = sqlite3.connect(self.config.paths.database)
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT mac, time, type, latitude, longitude, name
                    FROM devices
                    ORDER BY time;
            """)
            
            db_coords = cursor.fetchall()
            connection.close()

            if db_coords:
                coordinates.extend(db_coords)
        except Exception as exception:
            print(f"   ❌ Error reading {os.path.basename(self.config.paths.database)}: {exception}")
        return coordinates

    def build_gps_nodes(self) -> list[GPSCoordinateNode]:
        devices_data = self.get_all_devices_data()

        print("devices data:", len(devices_data))

        devices: list[Device] = []
        for data in devices_data:
            device_name: str = data[5]
            device_coordinate = DeviceCoordinate(
                time=int(data[1]),
                latitude=float(data[3]),
                longitude=float(data[4]),
            )

            device = next((x for x in devices if x.mac == data[0]), None)
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
                node = next((x for x in nodes if coordinate.time - x.time < NODE_TIME_MAX), None)
                if node == None:
                    node = GPSCoordinateNode(len(nodes) + 1, coordinate.time, gps_coordinate, [device], [], [])
                    nodes.append(node)
                else:
                    node.add_device(device)
                    node.latitudes.append(gps_coordinate.latitude)
                    node.lonitudes.append(gps_coordinate.longitude)

        print("nodes:", len(nodes))
        return nodes
    
    def load_rides(self, nodes: list[GPSCoordinateNode]):
        if len(nodes) == 0:
            print("[load_rides] nodes shounld't be enpty")
        self.rides = rides_from_nodes(nodes)

    def find_followers(self):
        map: list[DeviceDataMap] = []

        for ride in self.rides:
            for node in ride.nodes:
                for device in node.devices:
                    data = next((x for x in map if x.device.mac == device.mac), None)
                    if data == None:
                        data = DeviceDataMap(device=device, nodes=[node])
                        map.append(data)
                    else:
                        data.nodes.append(node)

        map.sort(key=lambda x: x.get_following_distance(), reverse=True)

        print("map:", len(map))
        print("length:", len(map[0].get_rides())) 

        all_rides_length = len(self.rides)
        all_rides_time = sum(ride.get_time() for ride in self.rides)
        all_rides_distance = sum(ride.get_distance() for ride in self.rides)

        for i in range(len(map)):
            percentage_length = len(map[i].get_rides()) / all_rides_length
            percentage_time = map[i].get_following_time() / all_rides_time
            percentage_distance = map[i].get_following_distance() / all_rides_distance
            if percentage_length > .2 and percentage_time > .2 and percentage_distance > .2:
                 print(
                    "rides:", len(map[i].get_rides()),
                    "nodes:", map[i].get_nodes_length(),
                    "mac:", map[i].device.mac,
                    "following time:", int(map[i].get_following_time() / 60),
                    "following distance:", int(map[i].get_following_distance()),
                    map[i].device.type,
                    map[i].device.name,
                )

    def start(self):
        print("Hello, World!")

        nodes = self.build_gps_nodes()
        self.load_rides(nodes)
        self.find_followers()

# TODO: logging
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CYT Detect if a device is following you")

    parser.add_argument('--config-path', type=str, default="config/config.json", help='Path to specific CYT configuration file')

    args = parser.parse_args()

    detector = DetectFollowingDevices(args.config_path)
    detector.start()
