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
from facenet_core import *


logging.basicConfig(level=logging.DEBUG)

def load_config():
    with open("config_in.yaml", "r", encoding="utf-8") as config_file:
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

def base64_to_pixmap(base64_str):
    image_data = base64.b64decode(base64_str)
    image = QImage.fromData(image_data)
    return QPixmap.fromImage(image).scaled(
        260, 200, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation
    )

def sync_tables():
    # Create engines for local SQLite and PostgreSQL databases
    pg_engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
    sqlite_engine = create_engine(local_db_path)

    # Fetch data from local SQLite
    local_tracking_history = pd.read_sql_table('tracking_history', sqlite_engine)
    local_tracking_history_error = pd.read_sql_table('tracking_history_error', sqlite_engine)

    # Convert the `id` and `user_id` to UUID for PostgreSQL
    def convert_to_uuid(val):
        try:
            if val and isinstance(val, str) and len(val) == 36:
                return uuid.UUID(val)
            else:
                return None
        except (ValueError, TypeError):
            return None

    # Apply conversion for tracking_history table with progress bar
    print("Converting tracking_history table UUIDs...")
    for col in tqdm(['id', 'user_id'], desc="Tracking History"):
        local_tracking_history[col] = local_tracking_history[col].apply(convert_to_uuid)

    # Apply conversion for tracking_history_error table with progress bar
    print("Converting tracking_history_error table UUIDs...")
    for col in tqdm(['id', 'user_id'], desc="Tracking History Error"):
        local_tracking_history_error[col] = local_tracking_history_error[col].apply(convert_to_uuid)

    # Convert local datetime to PostgreSQL timestamp for `time` field
    print("Converting datetime fields...")
    local_tracking_history['time'] = pd.to_datetime(local_tracking_history['time'])
    local_tracking_history_error['time'] = pd.to_datetime(local_tracking_history_error['time'])

    # Sync the data into PostgreSQL
    with pg_engine.connect() as conn:
        print("Syncing tracking_history table to PostgreSQL...")
        local_tracking_history.to_sql('tracking_history', conn, if_exists='replace', index=False)

        print("Syncing tracking_history_error table to PostgreSQL...")
        local_tracking_history_error.to_sql('tracking_history_error', conn, if_exists='replace', index=False)

    print("Sync complete.")

def sync_data_from_online_db():
    pg_engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
    sqlite_engine = create_engine(local_db_path)

    # Create MetaData instance for PostgreSQL
    pg_metadata = MetaData()
    pg_metadata.reflect(bind=pg_engine)

    # Specify the tables you want to copy
    tables_to_copy = ['departments', 'workshops', 'user_images', 'user_details']

    # Iterate over specified tables and copy schema and data to SQLite with tqdm progress bar
    for table_name in tqdm(tables_to_copy, desc="Copying tables"):
        if table_name in pg_metadata.tables:

            # Clear the table in SQLite before inserting new data
            with sqlite_engine.connect() as connection:
                connection.execute(text(f"DELETE FROM {table_name}"))
                tqdm.write(f"Cleared table: {table_name} in local SQLite")

            tqdm.write(f"Copying table: {table_name}")  # Use tqdm.write to avoid interrupting the progress bar
            pg_table = pg_metadata.tables[table_name]

            # Fetch data from PostgreSQL table
            data = pd.read_sql_table(table_name, pg_engine)

            # Check if the DataFrame is not empty before processing
            if not data.empty:
                # Convert UUID columns to strings and handle complex data
                for col in data.columns:
                    if data[col].dtype == 'object':
                        # Convert UUIDs to strings
                        if len(data[col]) > 0 and isinstance(data[col].iloc[0], uuid.UUID):
                            data[col] = data[col].astype(str)
                        
                        # Convert dictionaries or JSON-like objects to strings
                        elif isinstance(data[col].iloc[0], dict):
                            data[col] = data[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
            
            # Write data to SQLite table
            data.to_sql(table_name, sqlite_engine, if_exists='replace', index=False)

    print("Database copy complete.")



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

def qimage_to_numpy(qimage):
    # Convert QImage to byte array
    qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
    width = qimage.width()
    height = qimage.height()

    ptr = qimage.bits()
    ptr.setsize(height * width * 3)  # 3 bytes per pixel for RGB format
    arr = np.array(ptr).reshape(height, width, 3)  # Convert to a numpy array and reshape
    return arr

def sync_database():
    from sqlalchemy import create_engine, MetaData, Table
    import pandas as pd
    import uuid
    import json

    # Database connection URI for PostgreSQL
    pg_database_uri = f'postgresql://{user}:{password}@{host}:{port}/{database}'
    pg_engine = create_engine(pg_database_uri)

    # SQLite database URI
    sqlite_database_uri = 'sqlite:///local_attendance_tracking.db'
    sqlite_engine = create_engine(sqlite_database_uri)

    # Create MetaData instance for PostgreSQL
    pg_metadata = MetaData()
    pg_metadata.reflect(bind=pg_engine)

    # Specify the table to copy
    table_name = 'user_details'

    # Fetch data from PostgreSQL table
    pg_data = pd.read_sql_table(table_name, pg_engine)

    # Check if the DataFrame is not empty before processing
    if not pg_data.empty:
        # Convert UUID columns to strings and handle complex data
        for col in pg_data.columns:
            if pg_data[col].dtype == 'object':
                # Convert UUIDs to strings
                if len(pg_data[col]) > 0 and isinstance(pg_data[col].iloc[0], uuid.UUID):
                    pg_data[col] = pg_data[col].astype(str)
                
                # Convert dictionaries or JSON-like objects to strings
                elif isinstance(pg_data[col].iloc[0], dict):
                    pg_data[col] = pg_data[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)

        # Fetch existing local data from SQLite
        local_data = pd.read_sql_table(table_name, sqlite_engine)

        # If local data exists, compare and sync
        if not local_data.empty:
            # Find rows in local_data that are not in pg_data
            merged = local_data.merge(pg_data, on='id', how='left', indicator=True)
            rows_to_delete = merged[merged['_merge'] == 'left_only']['id']

            # Delete rows in SQLite that are not present in PostgreSQL
            if not rows_to_delete.empty:
                ids_to_delete = tuple(rows_to_delete)
                with sqlite_engine.connect() as conn:
                    conn.execute(f"DELETE FROM {table_name} WHERE id IN {ids_to_delete}")
        
        # Write PostgreSQL data to SQLite, replacing existing table
        pg_data.to_sql(table_name, sqlite_engine, if_exists='replace', index=False)

    print("Table sync complete.")


class LogCard(QtWidgets.QWidget):
    clicked_signal = pyqtSignal(object)

    def __init__(self, user_id, employee_code, user_name, timestamp, status, image_base64=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.employee_code = employee_code
        self.user_name = user_name
        self.timestamp = timestamp
        self.status = status
        self.image_base64 = image_base64

        self.setFixedSize(320, 320)
        self.setStyleSheet("border: 1px solid black; background-color: white;")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = QtWidgets.QGraphicsView(self.scene, self)
        self.view.setFixedSize(300, 300)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.layout.addWidget(self.view)

        message = f"ID: {self.employee_code}\nHọ Tên: {self.user_name}\nThời gian: {self.timestamp}\nĐIỂM DANH THÀNH CÔNG !!!"
        self.text_item = self.scene.addText(message)
        self.text_item.setTextWidth(260)
        self.text_item.setDefaultTextColor(QtGui.QColor("black"))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.text_item.setFont(font)
        self.text_item.setPos(10, 10)

        if self.image_base64:
            pixmap = base64_to_pixmap(self.image_base64)
            image_item = self.scene.addPixmap(pixmap)
            image_item.setPos(10, self.text_item.boundingRect().height() + 20)

        self.scene.setSceneRect(0, 0, 300, 300)
        self.clicked_signal.connect(self.handle_click)

    def handle_click(self):
        # Display full error information when the log card is clicked
        error_message = (f"ID: {self.employee_code}\n"
                        f"name: {self.user_name}\n"
                         f"Thời gian: {self.timestamp}\n"
                         f"BÁO LỖI THÀNH CÔNG ;.;")
        self.text_item.setPlainText(error_message)

        # Log the error directly to the database
        try:
            # Open a database connection
            engine = db.create_engine(local_db_path)
            connection = engine.connect()
            metadata = db.MetaData()
            tracking_history_error = db.Table('tracking_history_error', metadata, autoload_with=engine)

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
            logging.error(f"Error logging to database: {e}")
        
        finally:
            # Close the database connection
            connection.close()
            logging.debug("Database connection closed")

    def enterEvent(self, event):
        self.setStyleSheet("border: 1px solid black; background-color: lightgray;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("border: 1px solid black; background-color: white;")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        print("LogCard clicked!")
        self.clicked_signal.emit(self)

# Thread for capturing frames
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

class AttendanceCheckingWindow(object):
    def setupUi(self, MainWindow):
        self.MainWindow = MainWindow
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1920, 1080)

        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.camera_area_widget = QtWidgets.QLabel(parent=self.centralwidget)
        self.camera_area_widget.setGeometry(QtCore.QRect(30, 90, 1321, 900))
        self.camera_area_widget.setStyleSheet("""background-color:rgb(246, 247, 245);
                                               border: 1px solid black;
                                               """)
        self.camera_area_widget.setObjectName("camera_area_widget")
        self.camera_area_widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.thong_tin_diem_danh = QtWidgets.QScrollArea(parent=self.centralwidget)
        self.thong_tin_diem_danh.setGeometry(QtCore.QRect(1380, 90, 350, 900))
        self.thong_tin_diem_danh.setWidgetResizable(True)
        self.thong_tin_diem_danh.setObjectName("thong_tin_diem_danh")
        self.thong_tin_diem_danh.setStyleSheet("""background-color:rgb(246, 247, 245);
                                               border: 1px solid black;
                                               """)

        self.log_container = QtWidgets.QWidget()
        self.log_layout = QtWidgets.QVBoxLayout(self.log_container)
        self.log_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.log_layout.setSpacing(10)
        self.log_container.setLayout(self.log_layout)

        self.thong_tin_diem_danh.setWidget(self.log_container)

        self.last_detection_times = {}
        self.detection_count = {}

        self.lcdNumber = QtWidgets.QLCDNumber(parent=self.centralwidget)
        self.lcdNumber.setGeometry(QtCore.QRect(1100, 10, 241, 61))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.lcdNumber.setFont(font)
        self.lcdNumber.setObjectName("lcdNumber")
        self.lcdNumber.setDigitCount(8)
        self.lcdNumber.setStyleSheet("color: rgb(204, 0, 15);")

        self.label = QtWidgets.QLabel(parent=self.centralwidget)
        self.label.setGeometry(QtCore.QRect(1420, 20, 300, 41))
        font = QtGui.QFont()
        font.setFamily("Bahnschrift SemiBold")
        font.setPointSize(20)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.pushButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(30, 20, 131, 41))
        font = QtGui.QFont()
        font.setFamily("Bahnschrift SemiBold")
        font.setPointSize(20)
        self.pushButton.setFont(font)
        self.pushButton.setObjectName("pushButton")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1907, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.pushButton.clicked.connect(self.open_home_page)
        
        self.setup_database()
        # self.clear_images_folder()  # Ensure folder is cleared
        # self.load_images_from_database()  # Load images after clearing

        self.cap = cv2.VideoCapture(capture_id)
        self.deepface = Facenet(image_folder)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_lcd_time)
        self.timer.start()

        # self.main_frame = QtCore.QTimer()
        # self.main_frame.timeout.connect(self.update_frame_raw)
        # self.main_frame.start()
        # Initialize frame capture thread
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

    def update_frame_raw(self):
        try:
            ret, frame = self.cap.read()
            
            # Ensure a valid frame is read
            if not ret or frame is None:
                logging.warning("Failed to capture frame from camera.")
                return
            
            people = self.deepface.find(frame, distance_threshold)
            print(people)

            # if len(people) > 0:
            #     try:
            #         for person in people:
            #             print(f"person: {person}")
            #             user_id = person[0].split('/')[0]
            #             print(f"user: {user_id}")
            #             user_name = self.get_user_name(user_id)  # Assuming get_user_name is a method that retrieves the user's name
            #             print(f"user name: {user_name}")
            #             employee_code = self.get_employee_code(user_id)
            #             print(f"employee code: {employee_code}")

            #             if user_id not in self.detection_count:
            #                 self.detection_count[user_id] = 0
            #             self.detection_count[user_id] += 1

            #             if self.detection_count[user_id] >= 5 and self.should_log(user_id):
            #                 self.face_detected = True
            #                 self.last_detected_user_id = user_id
            #                 self.last_detection_time = time.time()
            #                 self.log_face_detected(user_id, user_name, ret, frame)
            #                 self.detection_count[user_id] = 0
            #     except KeyError as e:
            #         print(f"KeyError: {e}")
            #     except IndexError as e:
            #         print(f"IndexError: {e}")
            #     except Exception as e:
            #         print(f"An unexpected error occurred: {e}")

            # Process and display the frame
            self.display_frame(frame)
        
        except Exception as e:
            logging.error(f"Error while updating frame: {e}")

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
        try:
            # Resize the frame to fit the display area
            frame = cv2.resize(frame, (640, 480))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to QImage for display in the PyQt interface
            height, width, channel = frame.shape
            bytes_per_line = channel * width
            qt_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

            # Scale and display the image in the QLabel widget
            scaled_image = qt_image.scaled(self.camera_area_widget.width(), self.camera_area_widget.height(), 
                                        QtCore.Qt.AspectRatioMode.KeepAspectRatio, 
                                        QtCore.Qt.TransformationMode.SmoothTransformation)
            self.camera_area_widget.setPixmap(QPixmap.fromImage(scaled_image))
            self.camera_area_widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        except Exception as e:
            logging.error(f"Error displaying frame: {e}")

    def log_face_detected(self, user_id, user_name, ret, frame):
        # frame = cv2.flip(frame, 1)
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
                    # frame = cv2.flip(frame, 1)
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
        self.frame_capture_thread.stop()
        self.face_recognition_thread.stop()
        self.cleanup_resources()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = AttendanceCheckingWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())