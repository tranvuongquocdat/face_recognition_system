from sqlalchemy import create_engine, MetaData, Table, text
import json
import yaml
import uuid
import os
import sys
import time
import cv2
import sqlalchemy as db
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QTimer, QDateTime, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from deepface import DeepFace
from datetime import datetime
import logging
import subprocess
import base64
from io import BytesIO
import shutil
import numpy as np
import pandas as pd
from tqdm import tqdm 
from uuid import uuid4

class UpdateFrameThread(QThread):
    update_frame_signal = pyqtSignal(list, bool, object)

    def __init__(self, cap, parent=None):
        super().__init__(None)
        self.cap = cap
        self.running = True
        self.window = parent

    def run(self):
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    # frame = cv2.flip(frame, 1)

                    frame = cv2.resize(frame, (320, 240))

                    # Make sure the frame is in the correct format for DeepFace (which expects a numpy array if not a path)
                    people = DeepFace.find(img_path=frame, 
                                        db_path=image_folder, 
                                        model_name="Facenet", 
                                        distance_metric="euclidean_l2", 
                                        detector_backend="opencv", 
                                        enforce_detection=False)

                    # print(f"people: {people}")

                    # Check if people contains results
                    if len(people) > 0:
                        # The output from DeepFace.find() is a list of DataFrames, we take the first DataFrame
                        df_people = people[0]

                        # Filter out people based on the distance
                        filtered_people = df_people[df_people['distance'] <= distance_threshold].to_dict('records')
                        
                        # print(f"filtered people: {filtered_people}")
                    else:
                        filtered_people = []
                        print("No people found")

                    # Emit the signal with the filtered people and the frame
                    self.update_frame_signal.emit(filtered_people, ret, frame)
                # time.sleep(0.02)
            except Exception as e:
                print(f"Lỗi xảy ra trong luồng xử lý: {e}")

    def stop(self):
        self.running = False
        logging.debug("Stopping thread...")
        self.quit()
        self.wait()
        self.cap.release()
        logging.debug("Thread stopped and camera released.")

class UpdateFrameCascadeThread(QThread):
    update_cascade_signal = pyqtSignal(list, object)

    def __init__(self, cap, parent=None):
        super().__init__(None)
        self.cap = cap
        self.running = True
        self.window = parent

    def run(self):
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.resize(frame, (320, 240))
                    # frame = cv2.flip(frame, 1)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                    self.update_cascade_signal.emit(faces, frame)
                # time.sleep(0.02)
            except Exception as e:
                print(f"Lỗi xảy ra trong luồng xử lý: {e}")

    def stop(self):
        self.running = False
        self.cap.release()
        self.quit()