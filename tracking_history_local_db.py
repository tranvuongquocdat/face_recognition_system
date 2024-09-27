from PyQt6 import QtCore, QtGui, QtWidgets
import sqlalchemy as db
from sqlalchemy.sql import select
import pandas as pd
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QDialog, QCalendarWidget, QFileDialog,QScrollBar, QListView
from convert_check_in_data import *
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

from datetime import datetime, time
from datetime import datetime, timedelta
from calendar import monthrange
import pandas as pd
import base64
from PyQt6.QtGui import QImage, QPixmap

import yaml
import logging

logging.basicConfig(level=logging.DEBUG)

def load_config():
    with open("config_in.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)
    return config

# Load config
config = load_config()

# Access the database config for local and online databases
local_db_path = config['database']['local']['path']

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        self.main_window = MainWindow
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1900, 1070)
        font = QtGui.QFont()
        font.setPointSize(12)
        MainWindow.setFont(font)

        # Use a main layout for central widget
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.central_layout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.centralwidget.setLayout(self.central_layout)

        # Create a horizontal layout for the top buttons (including the home_page button)
        self.top_button_layout = QtWidgets.QHBoxLayout()
        self.central_layout.addLayout(self.top_button_layout)

        self.home_page = QtWidgets.QPushButton("Trang Chủ")
        self.home_page.setFont(QtGui.QFont("Arial", 15))
        self.top_button_layout.addWidget(self.home_page)

        # Create a horizontal layout for search controls
        self.search_layout = QtWidgets.QHBoxLayout()
        self.central_layout.addLayout(self.search_layout)

        self.ID_finding = QtWidgets.QLineEdit()
        font.setPointSize(12)
        self.ID_finding.setFont(font)
        self.ID_finding.setObjectName("ID_finding")
        self.search_layout.addWidget(self.ID_finding)
        # Kết nối phím Enter với hàm find_data
        self.ID_finding.returnPressed.connect(self.find_data)

        self.name_finding = QtWidgets.QLineEdit()
        self.name_finding.setFont(font)
        self.name_finding.setObjectName("name_finding")
        self.search_layout.addWidget(self.name_finding)
        # Kết nối phím Enter với hàm find_data
        self.name_finding.returnPressed.connect(self.find_data)

        self.in_out_finding = QtWidgets.QComboBox()
        self.in_out_finding.setFont(font)
        self.in_out_finding.setObjectName("in_out_finding")
        self.in_out_finding.addItem("")
        self.in_out_finding.addItem("")
        self.in_out_finding.addItem("")
        self.search_layout.addWidget(self.in_out_finding)

        # Add ComboBox for Departments (Phòng Ban)
        self.department_finding = QtWidgets.QComboBox()
        self.department_finding.setFont(font)
        self.department_finding.setObjectName("department_finding")
        self.search_layout.addWidget(self.department_finding)

        # Add ComboBox for Workshops (Xưởng)
        self.workshop_finding = QtWidgets.QComboBox()
        self.workshop_finding.setFont(font)
        self.workshop_finding.setObjectName("workshop_finding")
        self.search_layout.addWidget(self.workshop_finding)

        self.begin_time = QtWidgets.QPushButton("Ngày bắt đầu")
        self.search_layout.addWidget(self.begin_time)

        self.begin_hour_combo = QtWidgets.QComboBox()
        self.begin_hour_combo.addItems([f"{i:02d}" for i in range(24)])
        self.search_layout.addWidget(self.begin_hour_combo)

        self.begin_minute_combo = QtWidgets.QComboBox()
        self.begin_minute_combo.addItems([f"{i:02d}" for i in range(60)])
        self.begin_minute_combo.setMaxVisibleItems(10)
        self.search_layout.addWidget(self.begin_minute_combo)

        self.end_time = QtWidgets.QPushButton("Ngày kết thúc")
        self.search_layout.addWidget(self.end_time)

        self.end_hour_combo = QtWidgets.QComboBox()
        self.end_hour_combo.addItems([f"{i:02d}" for i in range(24)])
        self.end_hour_combo.setCurrentIndex(23)  # Set default to 23:00
        self.search_layout.addWidget(self.end_hour_combo)

        self.end_minute_combo = QtWidgets.QComboBox()
        self.end_minute_combo.addItems([f"{i:02d}" for i in range(60)])
        self.end_minute_combo.setMaxVisibleItems(10)
        self.end_minute_combo.setCurrentIndex(59)  # Set default to :59
        self.search_layout.addWidget(self.end_minute_combo)

        self.find_button = QtWidgets.QPushButton("Tìm Kiếm")
        self.find_button.setStyleSheet("background-color: darkblue; color: white;")
        self.search_layout.addWidget(self.find_button)

        self.export_button = QtWidgets.QPushButton("Xuất Excel")
        self.export_button.setStyleSheet("background-color: darkgreen; color: white;")
        self.search_layout.addWidget(self.export_button)

        # Create a table for displaying history
        self.history_tracking_widget = QtWidgets.QTableWidget()
        font.setPointSize(12)
        self.history_tracking_widget.setFont(font)
        self.history_tracking_widget.setObjectName("history_tracking_widget")
        self.history_tracking_widget.setColumnCount(7)
        self.history_tracking_widget.setRowCount(0)
        self.history_tracking_widget.setHorizontalHeaderLabels([
            "Mã Nhân Viên", "Tên Nhân Viên", "IN/OUT", "Thời Gian", "Phòng Ban", "Xưởng", "Ảnh Minh Chứng"
        ])
        self.history_tracking_widget.horizontalHeader().setStretchLastSection(True)
        self.history_tracking_widget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.central_layout.addWidget(self.history_tracking_widget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1900, 28))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.load_data()
        # Load unique values for department and workshop ComboBoxes
        self.load_comboboxes()

        self.home_page.clicked.connect(self.open_main_window)

        self.begin_time.clicked.connect(self.select_begin_date)
        self.end_time.clicked.connect(self.select_end_date)
        self.find_button.clicked.connect(self.find_data)
        self.export_button.clicked.connect(self.export_to_excel)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.ID_finding.setPlaceholderText(_translate("MainWindow", "Tìm kiếm theo mã nhân viên"))
        self.name_finding.setPlaceholderText(_translate("MainWindow", "Tìm kiếm theo tên nhân viên"))
        self.in_out_finding.setItemText(0, _translate("MainWindow", "IN/OUT"))
        self.in_out_finding.setItemText(1, _translate("MainWindow", "IN"))
        self.in_out_finding.setItemText(2, _translate("MainWindow", "OUT"))
        self.home_page.setText(_translate("MainWindow", "Trang Chủ"))

    def load_comboboxes(self):
        # Kết nối tới cơ sở dữ liệu
        engine = db.create_engine(local_db_path)
        connection = engine.connect()
        metadata = db.MetaData()
        metadata.reflect(bind=engine)

        departments = metadata.tables['departments']
        workshops = metadata.tables['workshops']

        # Truy vấn để lấy danh sách phòng ban
        department_stmt = select(departments.c.name.distinct())
        department_result = connection.execute(department_stmt)
        departments_list = [row[0] for row in department_result]
        self.department_finding.addItem("Phòng ban")
        self.department_finding.addItems(departments_list)

        # Truy vấn để lấy danh sách xưởng
        workshop_stmt = select(workshops.c.name.distinct())
        workshop_result = connection.execute(workshop_stmt)
        workshops_list = [row[0] for row in workshop_result]
        self.workshop_finding.addItem("Xưởng")
        self.workshop_finding.addItems(workshops_list)

        connection.close()

    def select_begin_date(self):
        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.update_begin_time)
        self.calendar.setWindowTitle("Chọn ngày bắt đầu")
        self.calendar.setGeometry(200, 200, 400, 300)
        self.calendar.show()

    def update_begin_time(self, date):
        self.begin_time.setText(date.toString("dd/MM/yyyy"))
        self.calendar.close()

    def select_end_date(self):
        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.update_end_time)
        self.calendar.setWindowTitle("Chọn ngày kết thúc")
        self.calendar.setGeometry(200, 200, 400, 300)
        self.calendar.show()

    def update_end_time(self, date):
        self.end_time.setText(date.toString("dd/MM/yyyy"))
        self.calendar.close()

    def load_data(self):
        # Kết nối tới cơ sở dữ liệu
        engine = db.create_engine(local_db_path)
        connection = engine.connect()
        metadata = db.MetaData()
        metadata.reflect(bind=engine)

        # Các bảng cần sử dụng
        tracking_history = metadata.tables['tracking_history']
        user_details = metadata.tables['user_details']
        departments = metadata.tables['departments']
        workshops = metadata.tables['workshops']

        # Câu truy vấn với employee_code thay vì user_id
        stmt = select(
            user_details.c.employee_code,  # Mã nhân viên
            user_details.c.full_name,      # Tên đầy đủ
            tracking_history.c.status,     # Trạng thái
            tracking_history.c.time,       # Thời gian
            departments.c.name.label('department_name'),  # Tên phòng ban
            workshops.c.name.label('workshop_name'),      # Tên xưởng
            tracking_history.c.image       # "Ảnh Minh Chứng"
        ).select_from(
            tracking_history
            .join(user_details, tracking_history.c.user_id == user_details.c.id)
            .join(departments, user_details.c.department_id == departments.c.id, isouter=True)
            .join(workshops, user_details.c.workshop_id == workshops.c.id, isouter=True)
        ).order_by(tracking_history.c.time.desc()) 

        result = connection.execute(stmt)

        # Đổ dữ liệu vào bảng
        self.history_tracking_widget.setRowCount(0)
        for row_number, row_data in enumerate(result):
            self.history_tracking_widget.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                if column_number == 6:  # Cột chứa "Ảnh Minh Chứng"
                    button = QtWidgets.QPushButton("Xem Ảnh")
                    button.setMaximumWidth(100)
                    button.clicked.connect(lambda checked, image=row_data[6]: self.show_image(image))

                    # Tạo widget chứa nút bấm và sắp xếp bố cục
                    widget = QtWidgets.QWidget()
                    layout = QtWidgets.QHBoxLayout(widget)
                    layout.addWidget(button)
                    layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)  # Canh giữa nút
                    layout.setContentsMargins(0, 0, 0, 0)  # Loại bỏ khoảng cách
                    widget.setLayout(layout)

                    self.history_tracking_widget.setCellWidget(row_number, column_number, widget)
                else:
                    item = QtWidgets.QTableWidgetItem(str(data))
                    item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)  # Chỉ hiển thị, không chỉnh sửa
                    if column_number == 4 or column_number == 5:  # Cột "Phòng Ban" và "Xưởng"
                        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)  
                    self.history_tracking_widget.setItem(row_number, column_number, item)



    def find_data(self):
        # Kết nối tới cơ sở dữ liệu
        engine = db.create_engine(local_db_path)
        connection = engine.connect()
        metadata = db.MetaData()
        metadata.reflect(bind=engine)

        # Các bảng cần sử dụng
        tracking_history = metadata.tables['tracking_history']
        user_details = metadata.tables['user_details']
        departments = metadata.tables['departments']
        workshops = metadata.tables['workshops']

        # Xây dựng bộ lọc
        filters = []
        if self.ID_finding.text():
            filters.append(user_details.c.employee_code == self.ID_finding.text())
        if self.name_finding.text():
            filters.append(user_details.c.full_name.like(f"%{self.name_finding.text()}%"))
        if self.in_out_finding.currentText() != "IN/OUT":
            filters.append(tracking_history.c.status == self.in_out_finding.currentText())

        # Bộ lọc cho phòng ban
        if self.department_finding.currentText() != "Phòng ban":
            filters.append(departments.c.name == self.department_finding.currentText())

        # Bộ lọc cho xưởng
        if self.workshop_finding.currentText() != "Xưởng":
            filters.append(workshops.c.name == self.workshop_finding.currentText())

        if self.begin_time.text() != "Ngày bắt đầu":
            begin_date = QtCore.QDate.fromString(self.begin_time.text(), "dd/MM/yyyy").toString("yyyy-MM-dd")
            begin_time = f"{self.begin_hour_combo.currentText()}:{self.begin_minute_combo.currentText()}:00"
            filters.append(tracking_history.c.time >= f"{begin_date} {begin_time}")
        if self.end_time.text() != "Ngày kết thúc":
            end_date = QtCore.QDate.fromString(self.end_time.text(), "dd/MM/yyyy").toString("yyyy-MM-dd")
            end_time = f"{self.end_hour_combo.currentText()}:{self.end_minute_combo.currentText()}:00"
            filters.append(tracking_history.c.time <= f"{end_date} {end_time}")

        # Câu truy vấn với employee_code, phòng ban và xưởng
        stmt = select(
            user_details.c.employee_code,
            user_details.c.full_name,
            tracking_history.c.status,
            tracking_history.c.time,
            departments.c.name.label('department_name'),
            workshops.c.name.label('workshop_name'),
            tracking_history.c.image
        ).select_from(
            tracking_history
            .join(user_details, tracking_history.c.user_id == user_details.c.id)
            .join(departments, user_details.c.department_id == departments.c.id, isouter=True)
            .join(workshops, user_details.c.workshop_id == workshops.c.id, isouter=True)
        ).where(*filters
        ).order_by(tracking_history.c.time.desc()) 

        result = connection.execute(stmt)

        # Đổ dữ liệu vào bảng
        self.history_tracking_widget.setRowCount(0)
        for row_number, row_data in enumerate(result):
            self.history_tracking_widget.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                if column_number == 6:
                    button = QtWidgets.QPushButton("Xem Ảnh")
                    button.setMaximumWidth(100)
                    button.clicked.connect(lambda checked, image=row_data[6]: self.show_image(image))
                    widget = QtWidgets.QWidget()
                    layout = QtWidgets.QHBoxLayout(widget)
                    layout.addWidget(button)
                    layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    widget.setLayout(layout)
                    self.history_tracking_widget.setCellWidget(row_number, column_number, widget)
                else:
                    item = QtWidgets.QTableWidgetItem(str(data))
                    item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                    if column_number == 4 or column_number == 5:
                        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    self.history_tracking_widget.setItem(row_number, column_number, item)




    def export_to_excel(self):
        # Check if begin time and end time are in the same month and year
        if self.begin_time.text() != "Ngày bắt đầu" and self.end_time.text() != "Ngày kết thúc":
            begin_date = QtCore.QDate.fromString(self.begin_time.text(), "dd/MM/yyyy")
            end_date = QtCore.QDate.fromString(self.end_time.text(), "dd/MM/yyyy")

            begin_month = begin_date.month()
            begin_year = begin_date.year()
            end_month = end_date.month()
            end_year = end_date.year()

            if begin_month != end_month or begin_year != end_year:
                QtWidgets.QMessageBox.warning(self.centralwidget, "Cảnh báo", "Không thể xuất Excel vì ngày bắt đầu và ngày kết thúc không cùng tháng và năm.")
                print("Cảnh báo", "Không thể xuất Excel vì ngày bắt đầu và ngày kết thúc không cùng tháng và năm.")
                return

        # Proceed with exporting if the dates are valid
        path, _ = QFileDialog.getSaveFileName(self.centralwidget, "Chọn nơi lưu file", "", "Excel Files (*.xlsx)")
        if path:
            data = []
            for row in range(self.history_tracking_widget.rowCount()):
                row_data = []
                for column in range(self.history_tracking_widget.columnCount()):
                    if column == 6:  # Now the 6th column is for the image link
                        item = self.history_tracking_widget.cellWidget(row, column)
                        # row_data.append(item.layout().itemAt(0).widget().text())  # Lấy link ảnh từ cơ sở dữ liệu
                    else:
                        item = self.history_tracking_widget.item(row, column)
                        row_data.append(item.text() if item else "")
                data.append(row_data)

            self.df = pd.DataFrame(data, columns=["Mã Nhân Viên", "Tên Nhân Viên", "IN/OUT", "Thời Gian", "Phòng Ban", "Xưởng"])  # Include "Xưởng"  # Include "Phòng Ban"
            output_df = convert_check_in_data_to_workshift(self.df, year=begin_year, month=begin_month)
            output_df.to_excel(path)
            os.chmod(path, 0o444)


    def show_image(self, base64_data):
        # Decode the base64 string
        image_data = base64.b64decode(base64_data)
        
        # Convert the binary data to QImage
        image = QImage.fromData(image_data)

        # Create a QPixmap from the QImage
        pixmap = QPixmap.fromImage(image)
        
        # Tạo một dialog mới để hiển thị ảnh
        dialog = QDialog()
        dialog.setWindowTitle("Xem Ảnh")
        layout = QVBoxLayout()

        label = QLabel()

        if pixmap.isNull():
            label.setText("Không thể tải ảnh. Vui lòng kiểm tra dữ liệu ảnh.")
        else:
            label.setPixmap(pixmap)
            label.setScaledContents(True)

        layout.addWidget(label)
        dialog.setLayout(layout)
        dialog.exec()

    def open_main_window(self):
        from main import Ui_MainWindow as MainWindowClass  # Import lớp giao diện của màn hình chính
        self.window = QtWidgets.QMainWindow()
        self.ui = MainWindowClass()
        self.ui.setupUi(self.window)
        self.window.showFullScreen()  # Hiển thị cửa sổ ở chế độ toàn màn hình
        self.main_window.close()  # Đóng cửa sổ hiện tại

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
