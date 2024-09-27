import sqlalchemy as db
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSignal
from datetime import datetime
import logging
from uuid import uuid4
from image_processing_utils import base64_to_pixmap

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