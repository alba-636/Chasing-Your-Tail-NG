import sqlite3
import os
import traceback

def getGPSCoordinateCount(db_files) -> int:
    total_gps_coords: int = 0
    for db_file in db_files:
        try:
            connection = sqlite3.connect(db_file)
            cursor = connection.cursor()
            cursor.execute("""
                SELECT COUNT(devmac)
                    FROM devices
                    WHERE avg_lat != 0 AND avg_lon != 0;
            """)
            gps_count = cursor.fetchone()[0]
            connection.close()

            total_gps_coords += int(gps_count)
        except Exception as exception:
            print(f"   ❌ Error reading {os.path.basename(db_file)}: {exception}")
            traceback.print_exc()
    return total_gps_coords

def getAllGPSCoordinates(db_files):
    coordinates = []
    for db_file in db_files:
        try:
            connection = sqlite3.connect(db_file)
            cursor = connection.cursor()
            
            # Get GPS locations with timestamps from this database
            cursor.execute("""
                SELECT DISTINCT avg_lat, avg_lon, first_time
                    FROM devices 
                    WHERE avg_lat != 0 AND avg_lon != 0 
                    ORDER BY first_time;
            """)
            
            db_coords = cursor.fetchall()
            connection.close()

            if db_coords:
                print(f"   📁 {os.path.basename(db_file)}: {len(db_coords)} GPS locations")
                coordinates.extend(db_coords)
        except Exception as exception:
            print(f"   ❌ Error reading {os.path.basename(db_file)}: {exception}")
            traceback.print_exc()
    return coordinates
