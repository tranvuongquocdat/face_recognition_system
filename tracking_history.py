from PyQt6 import QtCore, QtGui, QtWidgets
import sqlalchemy as db
from sqlalchemy.sql import select
import pandas as pd
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QDialog, QCalendarWidget, QFileDialog,QScrollBar, QListView
from utils.convert_check_in_data import *
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import select


from datetime import datetime, time
from datetime import datetime, timedelta
from calendar import monthrange
import pandas as pd
import base64
from PyQt6.QtGui import QImage, QPixmap
import yaml
from sqlalchemy import cast, String

def load_config():
    with open("config.yaml", 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            return None
    return config


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

        self.name_finding = QtWidgets.QLineEdit()
        self.name_finding.setFont(font)
        self.name_finding.setObjectName("name_finding")
        self.search_layout.addWidget(self.name_finding)

        self.in_out_finding = QtWidgets.QComboBox()
        self.in_out_finding.setFont(font)
        self.in_out_finding.setObjectName("in_out_finding")
        self.in_out_finding.addItem("")
        self.in_out_finding.addItem("")
        self.search_layout.addWidget(self.in_out_finding)

        # Add combo box for filtering by department
        self.department_combo = QtWidgets.QComboBox()
        self.department_combo.setFont(font)
        self.department_combo.setObjectName("department_combo")
        self.department_combo.addItem("Chọn Phòng Ban")  # Default option
        self.search_layout.addWidget(self.department_combo)

        # Add combo box for filtering by workshop
        self.workshop_combo = QtWidgets.QComboBox()
        self.workshop_combo.setFont(font)
        self.workshop_combo.setObjectName("workshop_combo")
        self.workshop_combo.addItem("Chọn Xưởng")  # Default option
        self.search_layout.addWidget(self.workshop_combo)


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

        self.connect_database()

        self.loaded_data = None  # To store the combined data from both databases

        self.load_data()
        # Call this method to populate department and workshop combo boxes
        self.populate_filter_combos()

        self.department_combo.currentTextChanged.connect(self.find_data)
        self.workshop_combo.currentTextChanged.connect(self.find_data)


        self.home_page.clicked.connect(self.open_main_window)

        self.begin_time.clicked.connect(self.select_begin_date)
        self.end_time.clicked.connect(self.select_end_date)
        self.find_button.clicked.connect(self.find_data)
        self.export_button.clicked.connect(self.export_to_excel)

    def connect_database(self):
        # Load configuration from the YAML file
        config = load_config()

        if config is None:
            print("Failed to load configuration")
            return

        # Connect to the local SQLite database
        self.local_engine = db.create_engine(config['database']['local']['path'])
        self.local_connection = self.local_engine.connect()

        # Connect to the online PostgreSQL database
        self.online_engine = db.create_engine(
            f"postgresql://{config['database']['online']['user']}:"
            f"{config['database']['online']['password']}@"
            f"{config['database']['online']['host']}:"
            f"{config['database']['online']['port']}/"
            f"{config['database']['online']['database']}"
        )
        self.online_connection = self.online_engine.connect()

        # Reflect the metadata for both databases
        self.metadata_local = db.MetaData()
        self.metadata_local.reflect(bind=self.local_engine)

        self.metadata_online = db.MetaData()
        self.metadata_online.reflect(bind=self.online_engine)

        # Load tables from the local and online databases
        self.local_tracking_history = self.metadata_local.tables['tracking_history']
        self.local_user_details = self.metadata_local.tables['user_details']
        self.online_tracking_history = self.metadata_online.tables['tracking_history']
        self.online_user_details = self.metadata_online.tables['user_details']
        self.online_departments = self.metadata_online.tables['departments']
        self.online_workshops = self.metadata_online.tables['workshops']



    def populate_filter_combos(self):
        # Clear existing items first
        self.department_combo.clear()
        self.workshop_combo.clear()

        # Add default options
        self.department_combo.addItem("Chọn Phòng Ban")
        self.workshop_combo.addItem("Chọn Xưởng")

        # Step 1: Query local database for distinct departments and workshops
        local_department_stmt = select(self.local_user_details.c.department_id.distinct())
        local_workshop_stmt = select(self.local_user_details.c.workshop_id.distinct())

        local_departments = self.local_connection.execute(local_department_stmt).fetchall()
        local_workshops = self.local_connection.execute(local_workshop_stmt).fetchall()

        # Step 2: Query online database for distinct departments and workshops
        online_department_stmt = select(self.online_user_details.c.department_id.distinct())
        online_workshop_stmt = select(self.online_user_details.c.workshop_id.distinct())

        online_departments = self.online_connection.execute(online_department_stmt).fetchall()
        online_workshops = self.online_connection.execute(online_workshop_stmt).fetchall()

        # Combine results and remove duplicates
        combined_departments = {dept[0] for dept in local_departments + online_departments if dept[0] is not None}
        combined_workshops = {ws[0] for ws in local_workshops + online_workshops if ws[0] is not None}

        # Fetch department names from the online database (since we have UUIDs, we need names)
        if combined_departments:
            department_name_stmt = select(
                cast(self.online_departments.c.id, String),
                self.online_departments.c.name
            ).where(cast(self.online_departments.c.id, String).in_(map(str, combined_departments)))
            department_names = self.online_connection.execute(department_name_stmt).fetchall()
            department_mapping = {str(dept[0]): dept[1] for dept in department_names}
        else:
            department_mapping = {}

        # Fetch workshop names from the online database
        if combined_workshops:
            workshop_name_stmt = select(
                cast(self.online_workshops.c.id, String),
                self.online_workshops.c.name
            ).where(cast(self.online_workshops.c.id, String).in_(map(str, combined_workshops)))
            workshop_names = self.online_connection.execute(workshop_name_stmt).fetchall()
            workshop_mapping = {str(ws[0]): ws[1] for ws in workshop_names}
        else:
            workshop_mapping = {}

        # Step 3: Populate the department and workshop combo boxes with the names
        for dept_id in combined_departments:
            department_name = department_mapping.get(dept_id, "Unknown")
            self.department_combo.addItem(department_name, dept_id)

        for ws_id in combined_workshops:
            workshop_name = workshop_mapping.get(ws_id, "Unknown")
            self.workshop_combo.addItem(workshop_name, ws_id)


    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.ID_finding.setPlaceholderText(_translate("MainWindow", "Tìm kiếm theo mã nhân viên"))
        self.name_finding.setPlaceholderText(_translate("MainWindow", "Tìm kiếm theo tên nhân viên"))
        self.in_out_finding.setItemText(0, _translate("MainWindow", "IN"))
        self.in_out_finding.setItemText(1, _translate("MainWindow", "OUT"))
        self.home_page.setText(_translate("MainWindow", "Trang Chủ"))
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

        # Step 1: Query local database for tracking history and user details
        local_stmt = select(
            self.local_user_details.c.employee_code,
            self.local_user_details.c.full_name,
            self.local_tracking_history.c.status,
            self.local_tracking_history.c.time,
            self.local_user_details.c.department_id,
            self.local_user_details.c.workshop_id,
            self.local_tracking_history.c.image
        ).select_from(
            self.local_tracking_history.join(
                self.local_user_details, self.local_tracking_history.c.user_id == self.local_user_details.c.id
            )
        ).order_by(self.local_tracking_history.c.time.desc())

        local_result = self.local_connection.execute(local_stmt).fetchall()

        # Step 2: Query the online PostgreSQL database for tracking history and user details
        online_stmt = select(
            self.online_user_details.c.employee_code,
            self.online_user_details.c.full_name,
            self.online_tracking_history.c.status,
            self.online_tracking_history.c.time,
            self.online_user_details.c.department_id,
            self.online_user_details.c.workshop_id,
            self.online_tracking_history.c.image
        ).select_from(
            self.online_tracking_history.join(
                self.online_user_details, cast(self.online_tracking_history.c.user_id, UUID) == self.online_user_details.c.id
            )
        ).order_by(self.online_tracking_history.c.time.desc())

        online_result = self.online_connection.execute(online_stmt).fetchall()

        # Combine the local and online results into one dataset
        combined_result = local_result + online_result

        # Collect all department_ids and workshop_ids for later mapping
        department_ids = set(row[4] for row in combined_result)
        workshop_ids = set(row[5] for row in combined_result)

        # Fetch department names from the online database with UUIDs casted to string
        department_mapping = {}
        if department_ids:
            online_department_stmt = select(
                cast(self.online_departments.c.id, String), 
                self.online_departments.c.name
            ).where(cast(self.online_departments.c.id, String).in_(map(str, department_ids)))
            department_results = self.online_connection.execute(online_department_stmt).fetchall()
            department_mapping = {str(row[0]): row[1] for row in department_results}

        # Fetch workshop names from the online database with UUIDs casted to string
        workshop_mapping = {}
        if workshop_ids:
            online_workshop_stmt = select(
                cast(self.online_workshops.c.id, String), 
                self.online_workshops.c.name
            ).where(cast(self.online_workshops.c.id, String).in_(map(str, workshop_ids)))
            workshop_results = self.online_connection.execute(online_workshop_stmt).fetchall()
            workshop_mapping = {str(row[0]): row[1] for row in workshop_results}

        # Step 3: Populate the data into the table, replacing department_id and workshop_id with their respective names
        self.history_tracking_widget.setRowCount(0)  # Clear the table before populating
        for row_number, row_data in enumerate(combined_result):
            self.history_tracking_widget.insertRow(row_number)

            # Replace department_id and workshop_id with names from the mappings
            department_id = str(row_data[4])
            workshop_id = str(row_data[5])

            department_name = department_mapping.get(department_id, "Unknown")
            workshop_name = workshop_mapping.get(workshop_id, "Unknown")

            row_data = list(row_data)  # Convert tuple to list to modify
            row_data[4] = department_name  # Replace department_id with department name
            row_data[5] = workshop_name  # Replace workshop_id with workshop name

            # Populate the table with the updated row_data
            for column_number, data in enumerate(row_data):
                if column_number == 6:  # Image column
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
                    item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)  # Prevent editing of cells
                    if column_number == 4 or column_number == 5:  # Center-align department and workshop columns
                        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    self.history_tracking_widget.setItem(row_number, column_number, item)
                    

        # Close the connections after data is loaded
        # self.local_connection.close()
        # self.online_connection.close()

    def find_data(self):
        # Step 1: Build filters for the queries
        local_filters = []
        online_filters = []

        if self.ID_finding.text():
            local_filters.append(self.local_tracking_history.c.user_id == self.ID_finding.text())
            online_filters.append(self.online_tracking_history.c.user_id == self.ID_finding.text())
        
        if self.name_finding.text():
            local_filters.append(self.local_user_details.c.full_name.like(f"%{self.name_finding.text()}%"))
            online_filters.append(self.online_user_details.c.full_name.like(f"%{self.name_finding.text()}%"))
        
        if self.in_out_finding.currentText():
            local_filters.append(self.local_tracking_history.c.status == self.in_out_finding.currentText())
            online_filters.append(self.online_tracking_history.c.status == self.in_out_finding.currentText())
        
        if self.department_combo.currentText() != "Chọn Phòng Ban":
            local_filters.append(self.local_user_details.c.department_id == self.department_combo.currentText())
            online_filters.append(self.online_user_details.c.department_id == self.department_combo.currentText())
        
        if self.workshop_combo.currentText() != "Chọn Xưởng":
            local_filters.append(self.local_user_details.c.workshop_id == self.workshop_combo.currentText())
            online_filters.append(self.online_user_details.c.workshop_id == self.workshop_combo.currentText())
        
        if self.begin_time.text() != "Ngày bắt đầu":
            begin_date = QtCore.QDate.fromString(self.begin_time.text(), "dd/MM/yyyy").toString("yyyy-MM-dd")
            begin_time = f"{self.begin_hour_combo.currentText()}:{self.begin_minute_combo.currentText()}:00"
            local_filters.append(self.local_tracking_history.c.time >= f"{begin_date} {begin_time}")
            online_filters.append(self.online_tracking_history.c.time >= f"{begin_date} {begin_time}")
        
        if self.end_time.text() != "Ngày kết thúc":
            end_date = QtCore.QDate.fromString(self.end_time.text(), "dd/MM/yyyy").toString("yyyy-MM-dd")
            end_time = f"{self.end_hour_combo.currentText()}:{self.end_minute_combo.currentText()}:00"
            local_filters.append(self.local_tracking_history.c.time <= f"{end_date} {end_time}")
            online_filters.append(self.online_tracking_history.c.time <= f"{end_date} {end_time}")

        # Step 2: Query both local and online databases with proper table prefixing
        local_stmt = select(
            self.local_user_details.c.employee_code,
            self.local_user_details.c.full_name,
            self.local_tracking_history.c.status,
            self.local_tracking_history.c.time,
            self.local_user_details.c.department_id,
            self.local_user_details.c.workshop_id,
            self.local_tracking_history.c.image
        ).select_from(
            self.local_tracking_history.join(self.local_user_details, self.local_tracking_history.c.user_id == self.local_user_details.c.id)
        ).where(*local_filters)

        online_stmt = select(
            self.online_user_details.c.employee_code,
            self.online_user_details.c.full_name,
            self.online_tracking_history.c.status,
            self.online_tracking_history.c.time,
            self.online_user_details.c.department_id,
            self.online_user_details.c.workshop_id,
            self.online_tracking_history.c.image
        ).select_from(
            self.online_tracking_history.join(self.online_user_details, cast(self.online_tracking_history.c.user_id, UUID) == self.online_user_details.c.id)
        ).where(*online_filters)

        # Execute both queries
        local_result = self.local_connection.execute(local_stmt).fetchall()
        online_result = self.online_connection.execute(online_stmt).fetchall()

        # Combine the results
        combined_result = local_result + online_result

        # Collect department and workshop IDs
        department_ids = set(row[4] for row in combined_result)
        workshop_ids = set(row[5] for row in combined_result)

        # Fetch department names from the online database
        department_mapping = {}
        if department_ids:
            online_department_stmt = select(
                cast(self.online_departments.c.id, String), 
                self.online_departments.c.name
            ).where(cast(self.online_departments.c.id, String).in_(map(str, department_ids)))
            department_results = self.online_connection.execute(online_department_stmt).fetchall()
            department_mapping = {str(row[0]): row[1] for row in department_results}

        # Fetch workshop names from the online database
        workshop_mapping = {}
        if workshop_ids:
            online_workshop_stmt = select(
                cast(self.online_workshops.c.id, String), 
                self.online_workshops.c.name
            ).where(cast(self.online_workshops.c.id, String).in_(map(str, workshop_ids)))
            workshop_results = self.online_connection.execute(online_workshop_stmt).fetchall()
            workshop_mapping = {str(row[0]): row[1] for row in workshop_results}

        # Step 3: Populate the table
        self.history_tracking_widget.setRowCount(0)  # Clear the table before populating
        for row_number, row_data in enumerate(combined_result):
            self.history_tracking_widget.insertRow(row_number)

            # Replace department and workshop IDs with names
            department_id = str(row_data[4])
            workshop_id = str(row_data[5])

            department_name = department_mapping.get(department_id, "Unknown")
            workshop_name = workshop_mapping.get(workshop_id, "Unknown")

            row_data = list(row_data)  # Convert tuple to list to modify
            row_data[4] = department_name
            row_data[5] = workshop_name

            # Populate the table with updated row_data
            for column_number, data in enumerate(row_data):
                if column_number == 6:  # Image column
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
        self.local_connection.close()
        self.online_connection.close()
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
