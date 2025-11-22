import sqlite3
import os
import argparse
import glob
from ConfigHelper import Config, load_config

class MacProbable:
    mac: str
    occurences: int

    def __init__(self, _mac, _occurences) -> None:
        self.mac = _mac
        self.occurences = _occurences

class MacFinder():
    config: Config

    def __init__(self, config_path: str):
        self.config = load_config(config_path)

    def get_mac_between(self, start: int, end: int) -> list[MacProbable]:
        """ Find all mac addresses between the given interval """

        db_pattern = self.config.paths.kismet_logs
        db_files = glob.glob(db_pattern)

        mac_probables: list[MacProbable] = []
        for db_file in db_files:
            try:
                connection = sqlite3.connect(db_file)
                cursor = connection.cursor()
                cursor.execute("""
                    SELECT sourcemac, COUNT(sourcemac) AS occurences
                        FROM packets
                        WHERE ts_sec > ? AND ts_sec < ?
                        GROUP BY sourcemac
                        ORDER BY occurences DESC;
                """, (start, end))
                result = cursor.fetchall()
                if len(result) > 0:
                    for raw in result:
                        mac_probables.append(MacProbable(raw[0], raw[1]))

                connection.close()

            except Exception as exception:
                print(f"   ❌ Error reading {os.path.basename(db_file)}: {exception}")

        return mac_probables

    def find_probables_in_database(self, start_at: int, end_at: int) -> list[MacProbable]:
        """ Find mac address present in given interval but not outside """

        before = self.get_mac_between(start_at - (60*30), start_at - 60)
        inner = self.get_mac_between(start_at - 60, end_at + 60)
        after = self.get_mac_between(end_at + 60, end_at + (60*30))

        probables: list[MacProbable] = []
        for probable in inner:
            if next((x for x in before if x.mac == probable.mac), None) == None and next((x for x in after if x.mac == probable.mac), None) == None:
                probables.append(probable)

        return probables

    def merge_probables(self, all_probables: list[list[MacProbable]]) -> list[MacProbable]:
        """ Find mac address present in all interval """

        result: list[MacProbable] = []
        for probable in all_probables[0]:
            occurences: int = 0
            keep = True
            for probables in all_probables:
                find = next((x for x in probables if x.mac == probable.mac), None)
                if find == None:
                    keep = False
                    break
                occurences += find.occurences

            if keep == True:
                result.append(MacProbable(probable.mac, occurences))

        return result

    def start(self, datas: list[tuple[str, str]]):
        all_probables: list[list[MacProbable]] = []
        for data in datas:
            all_probables.append(self.find_probables_in_database(int(data[0]), int(data[1])))

        probables = self.merge_probables(all_probables)

        output = []
        for probable in probables:
            output.append({ "mac": probable.mac, "occurences": probable.occurences })

        print(output)

def main():
    parser = argparse.ArgumentParser(description="CYT Find common mac address between several time range")

    parser.add_argument('--config-path', type=str, default="config/config.json", help='Path to specific CYT configuration file')
    parser.add_argument("--input", "-i", action="append", nargs=2, metavar=("start_at", "end_at"), help="Timestamp where the targeted device appears and Timestamp where the targeted device disappeared.", required=True)

    args = parser.parse_args()

    finder = MacFinder(args.config_path)
    finder.start(args.input)

if __name__ == "__main__":
    main()
