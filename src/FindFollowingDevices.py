import sqlite3
import os
import argparse
import math
from dataclasses import dataclass
from ConfigHelper import Config, load_config

@dataclass
class GPSCoordinate():
    latitude: float
    longitude: float

@dataclass
class GPSCoordinateNode():
    time: float
    gps_coordinate: GPSCoordinate
    devices: list[str]

    def add_device(self, device: str):
        if not device in self.devices:
            self.devices.append(device)

class DetectFollowingDevices():
    config: Config
    gps_nodes: list[GPSCoordinateNode] = []

    def __init__(self, config_path):
        self.config = load_config(config_path)

    def get_all_coordinates(self):
        coordinates = []
        try:
            connection = sqlite3.connect(self.config.paths.database)
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT mac, latitude, longitude, time
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

    def _calculate_distance(self, loc1: GPSCoordinate, loc2: GPSCoordinate) -> float:
        """Calculate distance between two GPS locations in meters"""
        # Haversine formula
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(loc1.latitude)
        lat2_rad = math.radians(loc2.latitude)
        delta_lat = math.radians(loc2.latitude - loc1.latitude)
        delta_lon = math.radians(loc2.longitude - loc1.longitude)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance

    def load_gps_nodes(self):
        coordinates = self.get_all_coordinates()

        print("coo", len(coordinates))

        for coordinate in coordinates:
            time = float(coordinate[3])
            mac: str = coordinate[0]
            gps_coordinate = GPSCoordinate(float(coordinate[1]), float(coordinate[2]))
            
            node = next((x for x in self.gps_nodes if self._calculate_distance(x.gps_coordinate, gps_coordinate) < 50 and x.time + 5 * 60 > time), None)
            if node == None:
                node = GPSCoordinateNode(time, gps_coordinate, [mac])
                self.gps_nodes.append(node)
            else:
                node.add_device(device=mac)

        print("nodes:", len(self.gps_nodes))

        # for node in self.gps_nodes:
        #     print("lat:", node.gps_coordinate.latitude, "lon:",node.gps_coordinate.longitude)
        #     print("time:", node.time)
        #     print("devices:", len(node.devices))

    def find_followers(self):
        print("find")

        map: list[list[str | int]] = []

        print("node:", len(self.gps_nodes[0].devices))

        for node in self.gps_nodes:
            for device in node.devices:
                data = next((x for x in map if x[0] == device), None)
                if data == None:
                    data = [device, 1]
                    map.append(data)
                else:
                    data[1] = int(data[1]) + 1

        map.sort(key=lambda x: x[1], reverse=True)

        print("map:", len(map))

        for i in range(10):
            print(map[i])


    def start(self):
        print("Hello, World!")

        self.load_gps_nodes()

        self.find_followers()

# TODO: logging
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CYT Detect if a device is following you")

    parser.add_argument('--config-path', type=str, default="config/config.json", help='Path to specific CYT configuration file')

    args = parser.parse_args()

    detector = DetectFollowingDevices(args.config_path)
    detector.start()
