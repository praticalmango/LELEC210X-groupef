"""
uart-reader.py
ELEC PROJECT - 210x
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
import serial
from serial.tools import list_ports

from classification.utils.plots import plot_specgram

import pickle

with open("C:/Users/franc/Documents/Codes/projet_elec/LELEC210X/classification/data/models/knn_model.pkl", "rb") as f:
    model = pickle.load(f)

PRINT_PREFIX = "DF:HEX:"
FREQ_SAMPLING = 10200
MELVEC_LENGTH = 20
N_MELVECS = 20

dt = np.dtype(np.uint16).newbyteorder("<")


def parse_buffer(line):
    line = line.strip()
    if line.startswith(PRINT_PREFIX):
        return bytes.fromhex(line[len(PRINT_PREFIX) :])
    else:
        print(line)
        return None


def reader(port=None):
    ser = serial.Serial(port=port, baudrate=115200)
    while True:
        line = ""
        while not line.endswith("\n"):
            line += ser.read_until(b"\n", size=2 * N_MELVECS * MELVEC_LENGTH).decode(
                "ascii"
            )
            print(line)
        line = line.strip()
        buffer = parse_buffer(line)
        if buffer is not None:
            buffer_array = np.frombuffer(buffer, dtype=dt)

            yield buffer_array


if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-p", "--port", help="Port for serial communication")
    args = argParser.parse_args()
    print("uart-reader launched...\n")

    if args.port is None:
        print(
            "No port specified, here is a list of serial communication port available"
        )
        print("================")
        port = list(list_ports.comports())
        for p in port:
            print(p.device)
        print("================")
        print("Launch this script with [-p PORT_REF] to access the communication port")

    else:
        input_stream = reader(port=args.port)
        msg_counter = 0

        for melvec in input_stream:
            msg_counter += 1
            
            

            print(f"MEL Spectrogram #{msg_counter}")
            
            # melvec is length 400 (20x20)
            mel_2d = melvec.reshape((N_MELVECS, MELVEC_LENGTH))   # shape = (20, 20)

            # ---- OPTION A: model expects FLAT vector ----
            X = melvec.reshape(1, -1)  # shape = (1, 400)

            # ---- OPTION B: model expects 2D image ----
            # X = mel_2d[np.newaxis, :, :]  # shape = (1, 20, 20)

            # ---- Classification ----
            # ---- NORMALIZE EXACTLY LIKE TRAINING ----
            norm = np.linalg.norm(X, axis=1, keepdims=True)
            X_norm = X / norm

            # ---- Predict ----
            prediction = model.predict(X_norm)

            print(f"Prediction #{msg_counter}: {prediction}")
            
            
            
            

            plt.figure()
            plot_specgram(
                melvec.reshape((N_MELVECS, MELVEC_LENGTH)).T,
                ax=plt.gca(),
                is_mel=True,
                title=f"MEL Spectrogram #{msg_counter}",
                xlabel="Mel vector",
            )
            plt.draw()
            plt.pause(0.001)
            plt.clf()
