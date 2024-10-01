from PyQt6 import QtCore, QtGui, QtWidgets
import qtawesome as qta  # Nếu dùng QtAwesome thì cài với pip install qtawesome
import sqlalchemy as db
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSignal
from datetime import datetime
import logging
from uuid import uuid4
import yaml

from utils.image_processing_utils import base64_to_pixmap

def load_config():
    with open("config/config_in.yaml", "r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    return config

# Load config
config = load_config()

# Access the database config for local and online databases
local_db_path = config['database']['local']['path']
camera_name = config['camera_name']['camera']
capture_id = config['capture_id']
distance_threshold = config['distance_threshold']

# Access the status config
status_in_out = config['status']['status']

width = 1920
height = 1080

def scale_height(size, height, original_height = 1080):
    return int(size/original_height * height)

def scale_width(size, width, original_width = 1920):
    return int(size/original_width * width)

class AttendanceCheckingWindowUI(object):
    def setupUi(self, MainWindow):
        global height, width
        self.MainWindow = MainWindow
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowTitle("Hệ thống điểm danh khuôn mặt")
        
        # Lấy kích thước màn hình một cách tự động
        screen_geometry = QtWidgets.QApplication.primaryScreen().availableGeometry()
        width = screen_geometry.width()
        height = screen_geometry.height()

        MainWindow.resize(width, height)

        # Thiết lập màu nền tối và các thành phần giao diện
        MainWindow.setStyleSheet("""
            QMainWindow {
                background-color: #2B2B2B;
            }
            QLabel{
                background-color: #383838;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 15px;
                padding: 1px;
            }
            QPushButton {
                background-color: #3E3E3E;
                color: white;
                border-radius: 15px;
                padding: 10px;
                font-size: 18px;
                border: 1px solid #444444;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QLCDNumber {
                background-color: #1E1E1E;
                color: #FF6F61;
                border-radius: 15px;
                border: 1px solid #444444;
            }
        """)

        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.camera_area_widget = QtWidgets.QLabel(parent=self.centralwidget)
        self.camera_area_widget.setGeometry(QtCore.QRect(scale_width(30, width), scale_height(90, height), scale_width(1450, width), scale_height(920, height)))
        self.camera_area_widget.setStyleSheet("""
            border-radius: 15px;
            border: 1px solid #444444;
        """)
        self.camera_area_widget.setObjectName("camera_area_widget")
        self.camera_area_widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


        self.thong_tin_diem_danh = QtWidgets.QScrollArea(parent=self.centralwidget)
        self.thong_tin_diem_danh.setGeometry(QtCore.QRect(scale_width(1500, width), scale_height(90, height), scale_width(340, width), scale_height(920, height)))
        self.thong_tin_diem_danh.setWidgetResizable(True)
        self.thong_tin_diem_danh.setStyleSheet("""
            QScrollArea {
                border-radius: 15px;
                border: 10px solid #444444;
                
            }
            QWidget {
                border-radius: 15px;
            }
        """)
        self.thong_tin_diem_danh.setObjectName("thong_tin_diem_danh")

        self.log_container = QtWidgets.QWidget()
        self.log_layout = QtWidgets.QVBoxLayout(self.log_container)
        self.log_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.log_container.setStyleSheet("""
            background-color: #444444;
            border-radius: 15px;
        """)
        self.log_container.setLayout(self.log_layout)
        self.thong_tin_diem_danh.setWidget(self.log_container)
        

        self.lcdNumber = QtWidgets.QLCDNumber(parent=self.centralwidget)
        self.lcdNumber.setGeometry(QtCore.QRect(scale_width(1250, width), scale_height(10, height), scale_width(241, width), scale_height(61, height)))
        font = QtGui.QFont()
        font.setPointSize(scale_width(20, width))
        self.lcdNumber.setFont(font)
        self.lcdNumber.setDigitCount(8)

        self.label = QtWidgets.QLabel(parent=self.centralwidget)
        self.label.setGeometry(QtCore.QRect(scale_width(1500, width), scale_height(20, height), scale_width(250, width), scale_height(50, height)))
        font = QtGui.QFont()
        font.setFamily("Roboto")
        font.setPointSize(scale_width(18, width))
        self.label.setFont(font)
        self.label.setObjectName("label")

        self.pushButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(scale_width(30, width), scale_height(20, height), scale_width(131, width), scale_height(50, height)))
        font = QtGui.QFont()
        font.setFamily("Roboto")
        font.setPointSize(scale_width(20, width))
        self.pushButton.setFont(font)
        self.pushButton.setObjectName("pushButton")

        # Thêm biểu tượng cho nút
        self.pushButton.setIcon(qta.icon('fa.home'))  # Nếu dùng QtAwesome

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, scale_width(1907, width), scale_height(22, height)))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.pushButton.clicked.connect(self.open_home_page)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Attendance System"))
        self.label.setText(_translate("MainWindow", "Thông tin điểm danh"))
        self.pushButton.setText(_translate("MainWindow", "Trang chủ"))

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

        # Set fixed size and dark theme consistent with the main window
        self.setFixedSize(scale_width(320, width), scale_width(320, width))
        self.setStyleSheet("""
            border: 1px solid #444444;
            background-color: #2B2B2B;
            border-radius: 15px;
        """)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 1)

        # Dark-themed QGraphicsView with rounded corners
        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = QtWidgets.QGraphicsView(self.scene, self)
        self.view.setFixedSize(scale_width(300, width), scale_width(300, width))
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setStyleSheet("""
            background-color: #383838;
            border: none;
            border-radius: 15px;
        """)
        self.layout.addWidget(self.view)

        # Message format with a modern font and white text color
        message = f"ID: {self.employee_code}\nHọ Tên: {self.user_name}\nThời gian: {self.timestamp}\nĐIỂM DANH THÀNH CÔNG !!!"
        self.text_item = self.scene.addText(message)
        self.text_item.setTextWidth(scale_width(260, width))
        self.text_item.setDefaultTextColor(QtGui.QColor("#FFFFFF"))
        
        font = QtGui.QFont()
        font.setFamily("Roboto")
        font.setPointSize(10)
        self.text_item.setFont(font)
        self.text_item.setPos(10, 10)

        if self.image_base64:
            pixmap = base64_to_pixmap(self.image_base64)
            image_item = self.scene.addPixmap(pixmap)
            image_item.setPos(10, self.text_item.boundingRect().height() + 20)

        self.scene.setSceneRect(0, 0, scale_width(300, width), scale_width(300, width))
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
            self.connection = engine.connect()
            metadata = db.MetaData()
            self.tracking_history_error = db.Table('tracking_history_error', metadata, autoload_with=engine)

            # Chuyển đổi thời gian từ QDateTime sang chuỗi
            time_object = self.timestamp
            logging.debug("Preparing to log to local database")

            # Generate a UUID for the primary key `id`
            log_id = str(uuid4())  # Chuyển UUID thành chuỗi

            # Insert into the tracking_history table in local database
            insert_query = db.insert(self.tracking_history_error).values(
                id=log_id,  # UUID dưới dạng chuỗi
                user_id=self.user_id,  
                time=time_object,
                status=status_in_out,
                image=self.image_base64,
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
            self.connection.close()
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


