import threading
import zmq
from enum import Enum
import time
from gps import *
import csv
import math
from collections import deque

# Enumeration for Results
class Results(Enum):
    Failure = 0
    Success = 1

# Encoding and Decoding Functions
def decoded(s):
    return int.from_bytes(s, 'little')

def encoded(value, length):
    return value.to_bytes(length, 'little')

class Integer8():
    def _init_(self):
        self.value = None

    def encode(self):
        if self.value is None:
            return None
        return encoded(self.value, 1)

    def decode(self, s):
        self.value = decoded(s[:1])
        return s[1:]

class Integer16():
    def _init_(self):
        self.value = None

    def encode(self):
        return encoded(self.value, 2)

    def decode(self, s):
        self.value = decoded(s[:2])
        return s[2:]

class Integer32():
    def _init_(self):
        self.value = None

    def encode(self):
        return encoded(self.value, 4)

    def decode(self, s):
        self.value = decoded(s[:4])
        return s[4:]

def sdecoded(s):
    return int.from_bytes(s, 'little', signed=True)

def sencoded(value, length):
    return value.to_bytes(length, 'little', signed=True)

class SInteger8():
    def _init_(self):
        self.value = None

    def encode(self):
        return sencoded(self.value, 1)

    def decode(self, s):
        self.value = sdecoded(s[:1])
        return s[1:]

class Integer48():
    def _init_(self):
        self.value = None

    def encode(self):
        return encoded(self.value, 6)

    def decode(self, s):
        self.value = s[:6].hex()
        return s[6:]

class Opaque():
    def _init_(self):
        self.value = None

    def encode(self):
        if self.value is None:
            return b''  # Return empty bytes if no value
        if isinstance(self.value, str):
            return self.value.encode('utf-8')
        return self.value  # Already bytes

# Enumeration for Modes
class Mode(Enum):
    SPS_MODE = 1
    ADHOC_MODE = 2

# WSMP Message Class
class HleWsmp():
    def _init_(self):
        self.mode = Integer8()
        self.ch_id = Integer8()
        self.time_slot = Integer8()
        self.data_rate = Integer8()
        self.tx_pow = SInteger8()
        self.ch_ld = Integer8()
        self.info = Integer8()
        self.usr_prio = Integer8()
        self.expiry_time = Integer8()
        self.mac = Integer48()
        self.psid = Integer32()
        self.dlen = Integer16()
        self.data = None

    def encode(self):
        out = (self.mode.encode() + self.ch_id.encode() + self.time_slot.encode() +
               self.data_rate.encode() + self.tx_pow.encode() + self.ch_ld.encode() +
               self.info.encode() + self.usr_prio.encode() + self.expiry_time.encode() +
               self.mac.encode() + self.psid.encode() + self.dlen.encode() + self.data)
        return out

# GPS Data Handling
gpsd = gps(mode=WATCH_ENABLE | WATCH_NEWSTYLE)
altitude_queue = deque(maxlen=10)  # Store the last 10 altitude readings

def get_position_data(gps):
    nx = gpsd.next()
    if nx['class'] == 'TPV':
        latitude = getattr(nx, 'lat', "Unknown")
        longitude = getattr(nx, 'lon', "Unknown")
        altitude = getattr(nx, 'alt', "Unknown")
        speed = getattr(nx, 'speed', "Unknown")
       
        # Smooth the altitude readings
        if altitude != "Unknown":
            altitude = float(altitude)
            altitude_queue.append(altitude)
            smoothed_altitude = sum(altitude_queue) / len(altitude_queue)
        else:
            smoothed_altitude = "Unknown"
       
        gps_data = [latitude, longitude, smoothed_altitude, speed]
        return gps_data

def get_cartesian(lat, lon):
    lat, lon = math.radians(lat), math.radians(lon)
    R = 6371  # Earth's radius in kilometers
    x = R * math.cos(lat) * math.cos(lon)
    y = R * math.cos(lat) * math.sin(lon)
    z = R * math.sin(lat)
    return x, y, z

def get_heading(a_location):
    if len(a_location) < 2:
        return 0  # Not enough data to compute heading
    off_x = a_location[-1][1] - a_location[-2][1]
    off_y = a_location[-1][0] - a_location[-2][0]
    heading = 90.00 + math.atan2(-off_y, off_x) * 57.2957795
    if heading < 0:
        heading += 360.00
    return heading

def fill_wsmp_content(data):
    hle_msg = HleWsmp()
    hle_msg.mode.value = Mode.SPS_MODE.value
    hle_msg.ch_id.value = 172
    hle_msg.time_slot.value = 0
    hle_msg.data_rate.value = 12
    hle_msg.tx_pow.value = -9
    hle_msg.ch_ld.value = 0
    hle_msg.info.value = 0
    hle_msg.expiry_time.value = 0
    hle_msg.usr_prio.value = 0
    hle_msg.mac.value = 16557351571215
    hle_msg.psid.value = 32
    hle_msg.dlen.value = len(data)
    hle_msg.data = bytes(data, 'utf-8')
    return hle_msg.encode()

def wsmp_operation():
    wsmp_context = zmq.Context()
    wsmp_socket = wsmp_context.socket(zmq.REQ)
    wsmp_socket.connect("tcp://localhost:5555")

    print("Server is listening for incoming connections...")
   
    a_location = [[0, 0]]
    file_name = '/home/guest1/usecases/cv2x/stationary_vehicle/gps_data.csv'

    # Initialize CSV file and write the header
    with open(file_name, "w", newline='') as csvfile:
        fieldnames = ['Latitude', 'Longitude', 'Altitude', 'Speed', 'Heading Angle']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
       # Initialize counters
    send_count = 0
    receive_count = 0

    while True:
        gps_data = get_position_data(gpsd)
        if gps_data:
            latitude = gps_data[0]
            longitude = gps_data[1]
            altitude = gps_data[2]
            speed = gps_data[3]
            a_location.append([latitude, longitude])
            head_ang = get_heading(a_location)

            # Print altitude in meters
            if altitude != "Unknown":
                altitude_meters = altitude
            else:
                altitude_meters = "Unknown"
           
            telemetry_data = (f"Telemetry Data:\n"
                              f"Latitude: {latitude}\n"
                              f"Longitude: {longitude}\n"
                              f"Altitude: {altitude_meters} meters\n"
                              f"Speed: {speed}\n"
                              f"Heading Angle: {head_ang}\n")

            print(telemetry_data)

            # Store the data in the CSV file
            with open(file_name, "a", newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow({
                    'Latitude': latitude,
                    'Longitude': longitude,
                    'Altitude': altitude_meters,
                    'Speed': speed,
                    'Heading Angle': head_ang
                })

            application_data = f"speed:{speed},latitude:{latitude},longitude:{longitude},altitude:{altitude_meters},heading_angle:{head_ang}"

            with open("OBU_TX.txt", "a") as file1:
                file1.write(application_data + "\n")

            print("length: ", len(application_data))

            result = fill_wsmp_content(application_data)
            print("data before sending wsmp and len: \n", result, len(result))

            wsmp_socket.send(result)
            send_count += 1  # Increment send counter
            msg = wsmp_socket.recv()
            receive_count += 1  # Increment receive counter
            print("Received WSMP Response: ", msg)
            print(f"Messages Sent: {send_count}, Messages Received: {receive_count}")

        time.sleep(0.1)

# WME Subscription Class
class Action(Enum):
    Add = 1
    Delete = 2

class WmeSub():
    def _init_(self):
        self.action = Integer8()
        self.psid = Integer32()
        self.appname = Opaque()

    def encode(self):
        # Ensure appname value is in bytes before encoding
        if isinstance(self.appname.value, str):
            self.appname.value = self.appname.value.encode('utf-8')
        out = self.action.encode() + self.psid.encode() + self.appname.encode()
        return out

def wme_operation():
    wme_context = zmq.Context()
    wme_socket = wme_context.socket(zmq.REQ)
    wme_socket.connect("tcp://localhost:9999")

    psid_sub_mag = WmeSub()
    psid_sub_mag.action.value = Action.Add.value
    psid_sub_mag.psid.value = 32
    psid_sub_mag.appname.value = "WAVE"  # This is a string, will be encoded in WmeSub.encode()

    print("Connecting to WME...")
    time.sleep(5)

    wme_socket.send(psid_sub_mag.encode())
    message = wme_socket.recv()
    print("Received WME Response: ", message)

if _name_ == '_main_':
    # Serial communication setup
    serial_port_path = '/dev/ttymxc3'
    baud_rate = 115200

    # Open the serial port as a file
    with open(serial_port_path, 'wb+', buffering=0) as ser_file:
        # Create service ID
        ser_file.write("AT+UBTGSER=4906276bda6a4a6cbf9473c61b96433c\r\n".encode())

        # Create characteristic ID
        ser_file.write("AT+UBTGCHA=49af5250f17646c5b99aa163a672c042,12,1,1,00,1,1\r\n".encode())

        # Start WME operation and WSMP operation threads
        wme_operation()
        app_operation_th = threading.Thread(target=wsmp_operation)
        app_operation_th.start()

        ser_file.write("AT+UBTGSER=4906276bda6a4a6cbf9473c61b96433c\r\n".encode())
