                                                                                               
import csv
from dronekit import connect, VehicleMode, LocationGlobalRelative
import time

# Connect to the Vehicle
connection_string = '/dev/ttyACM0'  # Adjust as per your setup
vehicle = connect(connection_string, baud=57600, wait_ready=True)

# Function to arm the drone and take off
def arm_and_takeoff(target_altitude):
    print("Basic pre-arm checks")
    
    # Check if vehicle is armable
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialize...")
        time.sleep(1)

    print("Arming vehicle")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.arm()

    # Wait until vehicle is armed
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)

    print("Taking off!")
    vehicle.simple_takeoff(target_altitude)

    # Wait until the vehicle reaches a safe height
    while True:
        print(" Altitude: ", vehicle.location.global_relative_frame.alt)
        if vehicle.location.global_relative_frame.alt >= target_altitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

# Function to navigate to a specified location
def goto_location(lat, lon, altitude):
    target_location = LocationGlobalRelative(lat, lon, altitude)
    vehicle.simple_goto(target_location)

# Function to read the latest latitude and longitude from CSV (ignore other data)
def read_latest_lat_lon_from_csv(filename):
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        if rows:  # Check if there are any rows
            latest_row = rows[-1]  # Get the last row
            lat = float(latest_row['Latitude'])
            lon = float(latest_row['Longitude'])
            return lat, lon
        else:
            return None, None

# Main script
if __name__ == "__main__":
