                                                                                          
import zmq
from enum import Enum
import threading
import time
from gps import *
import math
import csv
import paramiko
from scp import SCPClient

class Results(Enum):
    Failure = 0
    Success = 1

def decoded(s):
    return int.from_bytes(s, 'little')

def encoded(value, length):
    return value.to_bytes(length, 'little')

class Integer8():
    def __init__(self):
        self.value = None

    def encode(self):
        if self.value is None:
            return None
        return encoded(self.value, 1)

    def decode(self, s):
        self.value = decoded(s[:1])
        return s[1:]

class Integer16():
    def __init__(self):
        self.value = None

    def encode(self):
        return encoded(self.value, 2)

    def decode(self, s):
        self.value = decoded(s[:2])
        return s[2:]

class Integer32():
    def __init__(self):
        self.value = None

    def encode(self):
        out = encoded(self.value, 4)
        return out

    def decode(self, s):
        self.value = decoded(s[:4])
        return s[4:]

class Integer48():
