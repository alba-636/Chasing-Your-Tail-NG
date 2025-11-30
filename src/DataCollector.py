import asyncio
import json
import sqlite3
import argparse
from dataclasses import dataclass
from websockets.asyncio.client import connect
from ConfigHelper import Config, load_config

@dataclass
class DeviceData():
    mac: str
    time: int
    type: str
    latitude: float
    longitude: float
    name: str | None

    def print(self):
        print("mac:", self.mac, "time:", self.time, "type:", self.type, "latitude:", self.latitude, "longitude:", self.longitude, "name:", self.name)

class DataCollector():
    config: Config

    def __init__(self, config_path: str):
        self.config = load_config(config_path)        

        create_database(self.config.paths.database)

    async def start(self):
        # Kismet doc: https://www.kismetwireless.net/docs/api/devices/#realtime-device-monitoring
        async with connect(uri=f"ws://{self.config.kismet.url}:{self.config.kismet.port}/devices/monitor.ws?user={self.config.kismet.username}&password={self.config.kismet.password}") as websocket:
            await websocket.send('{ "monitor": "*", "request": 4242, "rate": 1 }')

            while True:
                data = await websocket.recv()
                self.insert_data(str(data))

    def insert_data(self, data: str):
        data_json = json.loads(data)

        if not "kismet.device.base.location" in data_json:
            print("Missing location data")
            return

        device_data = DeviceData(
            mac=data_json["kismet.device.base.macaddr"],
            time=int(data_json["kismet.device.base.last_time"]),
            type=data_json["kismet.device.base.type"],
            latitude=float(data_json["kismet.device.base.location"]["kismet.common.location.last"]["kismet.common.location.geopoint"][1]),
            longitude=float(data_json["kismet.device.base.location"]["kismet.common.location.last"]["kismet.common.location.geopoint"][0]),
            name=data_json["kismet.device.base.name"]
        )

        device_data.print()

        insert_device_in_database(self.config.paths.database, device=device_data)

def create_database(database_path: str):
    try:
        connection = sqlite3.connect(database_path)
        cursor = connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (  
                id INTEGER PRIMARY KEY AUTOINCREMENT,  
                mac TEXT NOT NULL,
                time INT NOT NULL,
                type TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                name TEXT
            );  
        """)

        connection.commit()
        connection.close()
    except Exception as exception:
        print(f"   ❌ Error reading {database_path}: {exception}")

def insert_device_in_database(database_path: str, device: DeviceData):
    try:
        connection = sqlite3.connect(database_path)
        cursor = connection.cursor()
        
        query = """
            INSERT INTO devices (mac, time, type, latitude, longitude, name)
                VALUES (?, ?, ?, ?, ?, ?);
        """
        params = (device.mac, device.time, device.type, device.latitude, device.longitude, device.name)

        cursor.execute(query, params)

        connection.commit()
        connection.close()
    except Exception as exception:
        print(f"   ❌ Error reading {database_path}: {exception}")

if __name__ == "__main__":
    print("Hello, World!")

    parser = argparse.ArgumentParser(description="CYT Alert via a Telegram channel when specific device is detected")

    parser.add_argument('--config-path', type=str, default="config/config.json", help='Path to specific CYT configuration file')

    args = parser.parse_args()

    data_collector = DataCollector(args.config_path)

    asyncio.run(data_collector.start())
