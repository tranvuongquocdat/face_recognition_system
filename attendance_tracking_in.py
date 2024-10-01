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

from utils.facenet_core import *
from utils.image_processing_utils import *
from utils.database_utils import *
from UI.attendance_ui import AttendanceCheckingWindowUI, LogCard  # Import the separated UI

cv2.ocl.setUseOpenCL(False)
cv2.setUseOptimized(False)

logging.basicConfig(level=logging.DEBUG)

def load_config():
    with open("config/config_in.yaml", "r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    return config

# Load config
config = load_config()

# Access the database config for local and online databases
local_db_path = config['database']['local']['path']
db_user = config['database']['online']['user']
db_password = config['database']['online']['password']
db_host = config['database']['online']['host']
db_port = config['database']['online']['port']
db_name = config['database']['online']['database']
image_folder = config['image_path']['image']
camera_name = config['camera_name']['camera']
capture_id = config['capture_id']
distance_threshold = config['distance_threshold']

# Access the status config
status_in_out = config['status']['status']

# Access the restart time config
restart_time = config['app']['restart_time']

class SyncThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer()
        self.timer.setInterval(10 * 60 * 1000)  # 10 phút (30 * 60 giây * 1000 mili giây)
        self.timer.timeout.connect(self.sync_tables)

    def run(self):
        self.timer.start()  # Bắt đầu đếm giờ
        self.exec()  # Đảm bảo luồng tiếp tục chạy để không kết thúc sau khi bắt đầu

    def sync_tables(self):
        # Tại đây bạn có thể gọi lại hàm sync_tables() đã được định nghĩa trước đó
        try:
            sync_tables()  # Thực hiện đồng bộ
        except Exception as e:
            print(f"Lỗi trong quá trình đồng bộ: {e}")

class FrameCaptureThread(QThread):
    frameCaptured = pyqtSignal(np.ndarray)  # Signal to send the captured frame

    def __init__(self, camera_id):
        super().__init__()
        self.camera_id = camera_id
        self.cap = None
        self.running = True

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_id)
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frameCaptured.emit(frame)
            time.sleep(0.03)  # Adjust frame capture interval as needed (30 FPS)

    def stop(self):
        self.running = False
        self.cap.release()

# Thread for face recognition
class FaceRecognitionThread(QThread):
    faceRecognized = pyqtSignal(list, object)  # Signal to send recognized faces data

    def __init__(self, deepface, distance_threshold):
        super().__init__()
        self.deepface = deepface
        self.distance_threshold = distance_threshold
        self.frame = None
        self.running = True

    def set_frame(self, frame):
        self.frame = frame

    def run(self):
        while self.running:
            if self.frame is not None:
                # Perform face recognition on the latest frame
                people = self.deepface.find(self.frame, self.distance_threshold)
                self.faceRecognized.emit(people, self.frame)
            time.sleep(0.1)  # Adjust processing interval as needed

    def stop(self):
        self.running = False

class AttendanceCheckingWindow(AttendanceCheckingWindowUI):  # Inherit from the UI class
    def __init__(self):
        super().__init__()
        self.deepface = None
        self.frame_capture_thread = None
        self.face_recognition_thread = None
        self.log_cards = []
        self.last_detection_times = {}
        self.detection_count = {}

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)  # Call the UI setup from the inherited class
        self.deepface = Facenet(image_folder)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_lcd_time)
        self.timer.start()

        self.setup_database()
        # self.clear_images_folder()  # Ensure folder is cleared
        # self.load_images_from_database()  # Load images after clearing

        self.frame_capture_thread = FrameCaptureThread(capture_id)
        self.frame_capture_thread.frameCaptured.connect(self.on_frame_captured)
        self.frame_capture_thread.start()

        # Initialize face recognition thread
        self.face_recognition_thread = FaceRecognitionThread(self.deepface, distance_threshold)
        self.face_recognition_thread.faceRecognized.connect(self.on_face_recognized)
        self.face_recognition_thread.start()

        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.capture_face)
        self.capture_timer.start()

        # Setup the daily restart timer
        self.restart_timer = QtCore.QTimer()
        self.restart_timer.timeout.connect(self.check_restart_time)
        self.restart_timer.start(10000)  # Check every minute

        self.face_detected = False
        self.last_detected_user_id = None
        self.last_detection_time = None
        self.log_cards = []


    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label.setText(_translate("MainWindow", "Thông tin điểm danh"))
        self.pushButton.setText(_translate("MainWindow", "Trang chủ"))

    def setup_database(self):
        self.engine = db.create_engine(local_db_path)
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.user_details = db.Table('user_details', self.metadata, autoload_with=self.engine)
        self.user_images = db.Table('user_images', self.metadata, autoload_with=self.engine)
        self.tracking_history = db.Table('tracking_history', self.metadata, autoload_with=self.engine)
        self.tracking_history_error = db.Table('tracking_history', self.metadata, autoload_with=self.engine)

        # Kết nối đến online database (PostgreSQL)
        self.online_engine = db.create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
        self.online_connection = self.online_engine.connect()

        # Bảng từ online database
        self.online_user_details = db.Table('user_details', self.metadata, autoload_with=self.online_engine)
        self.online_user_images = db.Table('user_images', self.metadata, autoload_with=self.online_engine)
        self.online_tracking_history = db.Table('tracking_history', self.metadata, autoload_with=self.online_engine)
        self.online_tracking_history_error = db.Table('tracking_history_error', self.metadata, autoload_with=self.online_engine)
        
        logging.info("Databases initialized and metadata loaded successfully.")

    def clear_images_folder(self):
        # Path to the 'images' folder

        # # Check if the folder exists
        if os.path.exists(image_folder):
        #     # Iterate through the items in the 'images' folder
        #     for item in os.listdir(images_path):
        #         item_path = os.path.join(images_path, item)
        #         # If the item is a folder, remove it and its contents
        #         if os.path.isdir(item_path):
                    # shutil.rmtree(item_path)

            shutil.rmtree(image_folder)
                    
        print("Cleared subfolders in 'images'")

    def load_images_from_database(self):
        # global image_path
        # Fetch all records from the user_images table in online database
        select_query = db.select(self.online_user_images)
        results = self.online_connection.execute(select_query).fetchall()
        print("Loaded images from online database")

        # Iterate over each record
        for result in results:
            user_id = result[1]  # Access 'user_id' using its index
            images = result[2]   # Access 'images' using its index

            # The images are stored as a single string, so split them by commas
            image_base64_list = images.split(',')

            # Create a subfolder for each user
            user_folder_path = os.path.join(image_folder, str(user_id))
            os.makedirs(user_folder_path, exist_ok=True)

            # Iterate over each base64-encoded image
            for index, image_base64 in enumerate(image_base64_list):
                # Decode the base64 image and save it as a .png file
                if len(image_base64) > 0:
                    image_data = base64.b64decode(image_base64)
                    image_path = os.path.join(user_folder_path, f"{result[0]}_{index}.png")  # Use 'id' index to create filename

                    with open(image_path, 'wb') as image_file:
                        image_file.write(image_data)

        print("Created image folders from online database")

    def update_lcd_time(self):
        current_time = time.strftime("%H:%M:%S")
        self.lcdNumber.display(current_time)

    def check_restart_time(self):
        """Check if the current time is 23:59 and restart the application."""
        print("checking restart time")
        current_time = QDateTime.currentDateTime().time()
        if current_time.hour() >= 23 and current_time.minute() >= 59:
            print("reng reng reng restart")
            sync_database()
            sync_data_from_online_db()
            self.restart_application()

    def restart_application(self):
        """Restart the application by closing and reopening it."""
        logging.info("Restarting application...")
        self.MainWindow.close()  # Simulate pressing the "X" button
        subprocess.Popen([sys.executable, "attendance_tracking.py"])

    def on_frame_captured(self, frame):
        """Slot to handle the frame captured from the camera."""
        # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        # faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        # for face in faces:
        #     x, y, w, h = face
        #     cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        # Display the frame
        self.display_frame(frame)

        # Send the frame to the face recognition thread
        self.face_recognition_thread.set_frame(frame)

    def on_face_recognized(self, people, frame):
        """Slot to handle face recognition results."""
        if len(people) > 0:
            for person in people:
                user_id = person[0].split('/')[0]
                print(f"user: {user_id}")
                user_name = self.get_user_name(user_id)  # Assuming get_user_name is a method that retrieves the user's name
                print(f"user name: {user_name}")
                employee_code = self.get_employee_code(user_id)
                print(f"employee code: {employee_code}")

                if user_id not in self.detection_count:
                    self.detection_count[user_id] = 0
                self.detection_count[user_id] += 1

                if self.detection_count[user_id] >= 5 and self.should_log(user_id):
                    self.face_detected = True
                    self.last_detected_user_id = user_id
                    self.last_detection_time = time.time()
                    self.log_face_detected(user_id, user_name, True, frame)
                    self.detection_count[user_id] = 0

    def update_frame_logic(self, people, ret, frame):
        if len(people) > 0:
            try:
                frame_area = frame.shape[0] * frame.shape[1]

                for person in people:
                    # Ensure the required keys are present
                    if 'source_w' in person and 'source_h' in person and 'identity' in person:
                        print(f"person: {person}")
                        face_area = person['source_w'] * person['source_h']
                        frame_area = frame.shape[0] * frame.shape[1]  # Assuming frame is defined and has shape attribute
                        face_area_ratio = face_area / frame_area

                        if face_area_ratio < 0.9:
                            user_id = person['identity'].split('/')[1]
                            print(f"user: {user_id}")
                            user_name = self.get_user_name(user_id)  # Assuming get_user_name is a method that retrieves the user's name
                            print(f"user name: {user_name}")
                            employee_code = self.get_employee_code(user_id)
                            print(f"employee code: {employee_code}")

                            if user_id not in self.detection_count:
                                self.detection_count[user_id] = 0
                            self.detection_count[user_id] += 1

                            if self.detection_count[user_id] >= 5 and self.should_log(user_id):
                                self.face_detected = True
                                self.last_detected_user_id = user_id
                                self.last_detection_time = time.time()
                                self.log_face_detected(user_id, user_name, ret, frame)
                                self.detection_count[user_id] = 0
            except KeyError as e:
                print(f"KeyError: {e}")
            except IndexError as e:
                print(f"IndexError: {e}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

    def update_frame_cascade_logic(self, faces, frame):
        if len(faces) > 0:
            for face in faces:
                self.draw_face_info(frame, face)
        
        self.display_frame(frame)


    def draw_face_info(self, frame, face):
        x, y, w, h = face
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    def get_user_name(self, user_id):
        select_query = db.select(self.user_details.c.full_name).where(self.user_details.c.id == user_id)
        result = self.connection.execute(select_query).fetchone()

        if result:
            print(f"result: %s" % result)
            return result[0]
        return "Unknown"

    def get_employee_code(self, user_id):
        select_query = db.select(self.user_details.c.employee_code).where(self.user_details.c.id == user_id)
        result = self.connection.execute(select_query).fetchone()

        if result:
            print(f"result: %s" % result)
            return result[0]
        return "Unknown"

    def display_frame(self, frame):
        frame = cv2.resize(frame, (640, 480))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.camera_area_widget.width(),
                                        self.camera_area_widget.height(),
                                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                        QtCore.Qt.TransformationMode.SmoothTransformation)
        self.camera_area_widget.setPixmap(QPixmap.fromImage(p))
        self.camera_area_widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def log_face_detected(self, user_id, user_name, ret, frame):
        frame = cv2.flip(frame, 1)
        print("start log face detected")
        self.capture_face(user_id, user_name, ret, frame)

    def should_log(self, user_id):
        if user_id in self.last_detection_times:
            if time.time() - self.last_detection_times[user_id] > 30:
                return True
            else:
                return False
        else:
            return True

    def capture_face(self, user_id=None, user_name=None, ret=False, frame=None):
        if self.face_detected and user_id:
            if self.should_log(user_id):
                if ret:
                    frame = cv2.flip(frame, 1)
                    now = QDateTime.currentDateTime()
                    image_base64 = self.convert_frame_to_base64(frame)
                    print("start log to db")
                    self.log_to_database(user_id, now, image_base64)
                    ID_log = "ID: " + user_id
                    user_name = self.get_user_name(user_id)
                    name_log = "Tên nhân viên: " + user_name
                    timestamp = now.toString('yyyy-MM-dd HH:mm:ss')
                    status = "IN"  # Adjust based on your logic
                    self.add_log_card(user_id, user_name, timestamp, status, image_base64=image_base64)
                    self.last_detection_times[user_id] = time.time()


    def convert_frame_to_base64(self, frame):
        _, buffer = cv2.imencode('.png', frame)
        return base64.b64encode(buffer).decode('utf-8')

    def log_to_database(self, user_id, now, image_base64):
        try:
            # Chuyển đổi thời gian từ QDateTime sang chuỗi
            time_object = datetime.strptime(now.toString("yyyy-MM-dd HH:mm:ss"), "%Y-%m-%d %H:%M:%S")
            logging.debug("Preparing to log to local database")

            # Generate a UUID for the primary key `id`
            log_id = str(uuid4())  # Chuyển UUID thành chuỗi

            # Insert into the tracking_history table in local database
            insert_query = db.insert(self.tracking_history).values(
                id=log_id,  # UUID dưới dạng chuỗi
                user_id=user_id,  
                time=time_object,
                status=status_in_out,
                image=image_base64,
                camera_id=camera_name
            )

            logging.debug(f"Executing SQL: {insert_query}")
            self.connection.execute(insert_query)
            self.connection.commit()
            logging.debug("Log to local database successful")
        except Exception as e:
            logging.error(f"Error logging to local database: {e}")

    def add_log_card(self, user_id, user_name, timestamp, status, image_base64=None):
        employee_code = self.get_employee_code(user_id)
        print(f"employee code: {employee_code}")
        log_card = LogCard(user_id, employee_code, user_name, timestamp, status, image_base64=image_base64, parent=self.log_container)
        self.log_layout.insertWidget(0, log_card)
        self.log_cards.insert(0, log_card)

        print("LogCard added and signal connected.")

        if len(self.log_cards) > 10:
            card_to_remove = self.log_cards.pop()
            self.log_layout.removeWidget(card_to_remove)
            card_to_remove.deleteLater()

    def extract_user_id_from_log(self, log_card):
        # Extract the log card text
        log_text = log_card.text_item.toPlainText()

        # Find the position of "ID:" in the text
        id_start = log_text.find("ID: ")
        if id_start != -1:
            # Extract the part of the text after "ID: "
            id_start += len("ID: ")
            # The ID should end at the next newline character
            id_end = log_text.find("\n", id_start)
            if id_end != -1:
                user_id = log_text[id_start:id_end].strip()
                return user_id
            else:
                # If no newline after ID, take the rest of the string
                user_id = log_text[id_start:].strip()
                return user_id
        return None  # Return None if ID is not found

    def log_error_to_database(self, user_id, now, image_base64):
        try:
            # Chuyển đổi thời gian từ QDateTime sang chuỗi
            time_object = datetime.strptime(now.toString("yyyy-MM-dd HH:mm:ss"), "%Y-%m-%d %H:%M:%S")
            logging.debug("Preparing to log to local database")

            # Generate a UUID for the primary key `id`
            log_id = str(uuid4())  # Chuyển UUID thành chuỗi

            # Insert into the tracking_history table in local database
            insert_query = db.insert(self.tracking_history_error).values(
                id=log_id,  # UUID dưới dạng chuỗi
                user_id=user_id,  
                time=time_object,
                status=status_in_out,
                image=image_base64,
                camera_id=camera_name
            )

            logging.debug(f"Executing SQL: {insert_query}")
            self.connection.execute(insert_query)
            self.connection.commit()
            logging.debug("Log error to local database successful")
        except Exception as e:
            logging.error(f"Error logging to local database: {e}")



    def open_home_page(self):
        self.cleanup_resources()  # Ensure all resources are properly released
        self.MainWindow.close()  # Simulate pressing the "X" button
        subprocess.Popen([sys.executable, "main.py"])  # Restart main.py

    def cleanup_resources(self):
        logging.debug("Cleaning up resources...")

        if hasattr(self, 'thread_frame') and self.thread_frame.isRunning():
            self.thread_frame.stop()
            self.thread_frame.wait()

        if hasattr(self, 'thread_frame_cascade') and self.thread_frame_cascade.isRunning():
            self.thread_frame_cascade.stop()
            self.thread_frame_cascade.wait()

        if hasattr(self, 'capture_timer') and self.capture_timer.isActive():
            self.capture_timer.stop()

        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()

        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()

        logging.debug("Resources cleaned up.")

    def closeEvent(self, event):
        self.cleanup_resources()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = AttendanceCheckingWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())