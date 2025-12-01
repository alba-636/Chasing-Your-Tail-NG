import sqlite3
import os
import argparse
import math
from dataclasses import dataclass
from ConfigHelper import Config, load_config
from DataCollector import DeviceData

@dataclass
class GPSCoordinate():
    latitude: float
    longitude: float

@dataclass
class GPSCoordinateNode():
    time: float
    gps_coordinate: GPSCoordinate
    devices: list[DeviceData]

    def add_device(self, device: DeviceData):
        if next((x for x in self.devices if x.mac == device.mac), None) == None:
            self.devices.append(device)

class DetectFollowingDevices():
    config: Config
    gps_nodes: list[GPSCoordinateNode] = []

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
        devices_data = self.get_all_devices_data()

        print("devices data:", len(devices_data))

        for data in devices_data:
            device = DeviceData(
                mac=data[0],
                time=int(data[1]),
                type=data[2],
                latitude=float(data[3]),
                longitude=float(data[4]),
                name=data[5],
            )
            gps_coordinate = GPSCoordinate(device.latitude, device.longitude)
            
            node = next((x for x in self.gps_nodes if self._calculate_distance(x.gps_coordinate, gps_coordinate) < 50 and x.time + 5 * 60 > device.time), None)
            if node == None:
                node = GPSCoordinateNode(device.time, gps_coordinate, [device])
                self.gps_nodes.append(node)
            else:
                node.add_device(device)

        print("nodes:", len(self.gps_nodes))

        # for node in self.gps_nodes:
        #     print("lat:", node.gps_coordinate.latitude, "lon:",node.gps_coordinate.longitude)
        #     print("time:", node.time)
        #     print("devices:", len(node.devices))

    def find_followers(self):
        print("find")

        map: list[list] = []

        print("node:", len(self.gps_nodes[0].devices))

        for node in self.gps_nodes:
            for device in node.devices:
                data = next((x for x in map if x[0].mac == device.mac), None)
                if data == None:
                    data = [device, 1]
                    map.append(data)
                else:
                    data[1] = data[1] + 1

        map.sort(key=lambda x: x[1], reverse=True)

        print("map:", len(map))

        for i in range(len(map)):
            percentage = map[i][1] / len(self.gps_nodes)
            if percentage > .5:
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
