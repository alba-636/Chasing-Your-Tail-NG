import asyncio
import json
import requests
import time
from websockets.asyncio.client import connect
from multiprocessing import Process
from src.ConfigHelper import Config, load_config

class TargetDevices:
    title: str
    mac_addresses: list[str]
    is_detected: bool

    def __init__(self, _title: str, _mac_addresses: list[str]):
        self.title = _title
        self.mac_addresses = _mac_addresses
        self.is_detected = False

class TargetDetector():
    config: Config

    def __init__(self):
        self.config = load_config("config/config.json")

    # TODO: Get full list from remote API?
    def load_traget_devices(self) -> list[TargetDevices]:
        return []

    def send_message(self, message):
        uri = f"https://api.telegram.org/bot{self.config.telegram.bot_token}/sendMessage"
        data = { "chat_id": self.config.telegram.chat_id, "text": message }
        requests.post(uri, json=data)

    # TODO: request only required fields
    def get_device(self, mac):
        uri = f"http://{self.config.kismet.username}:{self.config.kismet.password}@{self.config.kismet.url}:{self.config.kismet.port}/devices/by-mac/{mac}/devices.json"
        response = requests.get(uri)
        return response.json()

    def monitor_detected_target(self, target: TargetDevices, mac: str):
        print("Start monitoring device:", mac, "of:", target.title)

        target.is_detected = True

        self.send_message(f"Target Detected!\nTitle: {target.title}\nDevice: {mac}")

        is_lost = False
        while not is_lost:
            time.sleep(20)

            device = self.get_device(mac)
            last_time = device[0]["kismet.device.base.last_time"] if len(device) > 0  else 0
            now = time.time()
            last_seen = int(now - last_time)

            if last_seen > 90:
                is_lost = True
                self.send_message(f"Target Lost!\nTitle: {target.title}\nDevice: {mac}")
                continue
            elif last_seen > 20:
                self.send_message(f"{target.title} not detected since {last_seen} seconds!")
                continue
                
            self.send_message(f"{target.title} still detected!")

        target.is_detected = False

    async def start(self):
        targets = self.load_traget_devices()
        print(f"Track {len(targets)} targets")

        processes = []

        async with connect(uri=f"ws://{self.config.kismet.url}:{self.config.kismet.port}/eventbus/events.ws?user={self.config.kismet.username}&password={self.config.kismet.password}") as websocket:
            print("Websocket connected")
            await websocket.send('{"SUBSCRIBE": "MESSAGE"}')
            print("Websocket subscribed to MESSAGE")

            while True:
                message = await websocket.recv()
                obj = json.loads(message)
                message = obj["MESSAGE"]["kismet.messagebus.message_string"]

                if not ("Detected new" in message and "device" in message):
                    continue

                for target in targets:
                    if target.is_detected:
                        continue
                    
                    for mac in target.mac_addresses:
                        if mac in message:
                            process = Process(target=self.monitor_detected_target, args=(target, mac))
                            process.start()

        # Wait all processes to ends!
        for process in processes:
            process.join()

# TODO: arguments & logging
if __name__ == "__main__":
    detector = TargetDetector()
    asyncio.run(detector.start())
