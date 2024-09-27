import sys
import os
import pandas as pd
import cv2
import base64
import tempfile
import uuid
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QHBoxLayout, QAbstractItemView,
    QMessageBox, QLabel, QDialog, QFormLayout, QHeaderView, QSizePolicy, QFileDialog, 
)
from PyQt6.QtGui import QColor, QPixmap, QPainter, QFont, QImage, QPen
from PyQt6.QtCore import Qt, QRect, QTimer, QBuffer, QIODevice
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from deepface import DeepFace

import warnings
warnings.filterwarnings("ignore")

user = "hrm"
password = "hrm"
host = "35.223.205.197"  
port = "5432"  
database = "attendance_tracking"

# Database connection URI
DATABASE_URI = f'postgresql://{user}:{password}@{host}:{port}/{database}'

# Create a SQLAlchemy engine
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

# Create a MetaData instance and reflect the database schema
metadata = MetaData()
metadata.reflect(bind=engine)

# Access the reflected tables
user_details = metadata.tables['user_details']
tracking_history = metadata.tables['tracking_history']
user_images = metadata.tables['user_images']
departments = metadata.tables['departments'] 
workshops = metadata.tables['workshops'] 

def fetch_employee_data(order_by='Mã NV'):
    session = Session()

    query = session.query(
        user_details.c.employee_code.label('Mã NV'),
        user_details.c.full_name.label('Tên NV'),
        departments.c.name.label('Phòng ban'),
        workshops.c.name.label('Xưởng'),
        user_images.c.images.label('Ảnh hiện tại') 
    ).outerjoin(
        departments, departments.c.id == user_details.c.department_id  # JOIN với bảng departments
    ).outerjoin(
        workshops, workshops.c.id == user_details.c.workshop_id  # JOIN với bảng workshops
    ).outerjoin(
        user_images, user_images.c.user_id == user_details.c.id  # JOIN với bảng user_images
    ).distinct()

    # Sắp xếp theo Mã NV hoặc Tên NV
    if order_by == 'Mã NV':
        query = query.order_by(user_details.c.employee_code) 
    elif order_by == 'Tên NV':
        query = query.order_by(user_details.c.full_name) 

    # Execute query và xử lý kết quả
    data = query.all()
    processed_data = []

    for record in data:
        # Xử lý dữ liệu hình ảnh
        if record[4]:
            images_base64 = record[4].split(',')
            image_status = 'Đã có' if len(images_base64) > 0 else "Chưa đủ 5 ảnh"
        else:
            image_status = "Chưa đủ 5 ảnh"

        # Ghi nhận kết quả cho mỗi nhân viên
        processed_data.append({
            'Mã NV': record[0],
            'Tên NV': record[1],
            'Phòng ban': record[2] if record[2] else 'Chưa rõ',
            'Xưởng': record[3] if record[3] else 'Chưa rõ',
            'Ảnh hiện tại': image_status,
            'Thiết lập': ''  # Placeholder cho các thiết lập khác
        })

    df = pd.DataFrame(processed_data)
    session.close()

    return df

#class for image frame in chinh sua
class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap_image = QPixmap()
        self.setFixedSize(200, 200)
        self.status_label = QLabel(self) 
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px;")
        self.status_label.setGeometry(0, 160, 200, 30)

    def setPixmap(self, pixmap):
        self.pixmap_image = pixmap
        self.update()
        self.status_label.clear() 

    def paintEvent(self, event):
        painter = QPainter(self)
        img_size = 195

        if not self.pixmap_image.isNull():
            painter.drawPixmap(0, 0, img_size, img_size, self.pixmap_image.scaled(img_size, img_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            delete_icon_rect = QRect(img_size - 30, 10, 20, 20)
            painter.setBrush(QColor(255, 0, 0))
            painter.drawRect(delete_icon_rect)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(delete_icon_rect, Qt.AlignmentFlag.AlignCenter, "X")
        else:
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont('Arial', 50, QFont.Weight.Bold))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "+")

    def mousePressEvent(self, event):
        delete_icon_rect = QRect(self.width() - 30, 10, 20, 20)
        if delete_icon_rect.contains(event.pos()):
            self.clearImage()
        else:
            self.parent().change_image_slot(self)

    def clearImage(self):
        self.pixmap_image = QPixmap()
        self.update()
        self.status_label.clear() 

    def convert_to_base64(self):
        if not self.pixmap_image.isNull():
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            self.pixmap_image.save(buffer, "PNG")
            return base64.b64encode(buffer.data()).decode('utf-8')
        return ""

    def load_from_base64(self, base64_str):
        if base64_str:
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(base64_str))
            self.setPixmap(pixmap)

#class for chinh sua button
class EditEmployeeDialog(QDialog):
    def __init__(self, employee_data, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Chỉnh sửa thông tin nhân viên')
        self.setFixedSize(1000, 700)

        self.employee_data = employee_data
        self.engine = engine  
        self.image_paths = []
        self.face_verified = False

        self.layout = QVBoxLayout()

        self.info_layout = QFormLayout()
        font = QFont()
        font.setPointSize(14)  

        self.id_label = QLabel(str(self.employee_data['Mã NV']))
        self.id_label.setFont(font)
        self.name_label = QLabel(self.employee_data['Tên NV'])
        self.name_label.setFont(font)
        self.department_label = QLabel(self.employee_data['Phòng ban'])
        self.department_label.setFont(font)
        self.workshop_label = QLabel(self.employee_data['Xưởng'])
        self.workshop_label.setFont(font)

        self.info_layout.addRow('Mã NV:', self.id_label)
        self.info_layout.addRow('Tên NV:', self.name_label)
        self.info_layout.addRow('Phòng ban:', self.department_label)
        self.info_layout.addRow('Xưởng:', self.workshop_label)

        self.layout.addLayout(self.info_layout)

        self.status_label = QLabel("Chưa xác minh khuôn mặt")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(font)
        self.layout.addWidget(self.status_label) 

        self.image_layout = QHBoxLayout()
        self.image_layout.setSpacing(30)  
        self.image_labels = []

        for _ in range(5):
            label = ImageLabel(self)
            self.image_labels.append(label)
            self.image_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout.addLayout(self.image_layout)

        self.button_layout = QHBoxLayout()
        self.change_image_button = QPushButton('Thay đổi ảnh')
        self.capture_image_button = QPushButton('Chụp ảnh')
        self.save_exit_button = QPushButton('Lưu và Thoát')

        self.button_layout.addWidget(self.change_image_button)
        self.button_layout.addWidget(self.capture_image_button)
        self.button_layout.addWidget(self.save_exit_button)

        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

        # connect buttons
        self.change_image_button.clicked.connect(self.change_images)
        self.capture_image_button.clicked.connect(self.open_camera_capture_dialog)
        self.save_exit_button.clicked.connect(self.save_and_exit)

        # Load images from database if they exist
        self.load_images_from_db()
    
    def open_camera_capture_dialog(self):
        camera_dialog = CameraCaptureDialog(self)
        camera_dialog.exec()
    
    def update_image_frame(self, user_id):
        self.load_images_from_db()
        self.verify_faces()
    
    def add_image_to_frame(self, pixmap, index):
        if index < len(self.image_labels):
            self.image_labels[index].setPixmap(pixmap)

    def load_images_from_db(self):
        Session = sessionmaker(bind=self.engine)
        session = Session()

        # Truy vấn để lấy id (UUID) từ bảng user_details dựa trên Mã NV (employee_code)
        user_detail = session.query(user_details).filter_by(employee_code=self.employee_data['Mã NV']).first()

        if user_detail and user_detail.id:  # Kiểm tra nếu user_id tồn tại
            # Truy vấn user_images bằng user_id từ bảng user_details
            user_images_result = session.query(user_images).filter_by(user_id=user_detail.id).first()

            images_base64 = []  

            # Nếu có dữ liệu hình ảnh thì tách chuỗi base64 và tải ảnh
            if user_images_result and user_images_result.images:
                images_base64 = user_images_result.images.split(',')
                for i, base64_str in enumerate(images_base64):
                    if i < len(self.image_labels):
                        self.image_labels[i].load_from_base64(base64_str)
                
            if len(images_base64) == 5:
                self.verify_faces() 

    def change_images(self):
        self.open_image_dialog(self.image_labels)

    def change_image_slot(self, label):
        file_dialog = QFileDialog(self)
        file_name, _ = file_dialog.getOpenFileName(self, "Chọn ảnh", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_name:
            pixmap = QPixmap(file_name).scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(pixmap)

            self.verify_faces()

    def open_image_dialog(self, labels):
        file_dialog = QFileDialog(self)
        file_names, _ = file_dialog.getOpenFileNames(self, "Chọn ảnh", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")

        if file_names:
            empty_slots = [i for i, label in enumerate(labels) if label.pixmap_image.isNull()]
            available_slots = len(empty_slots)

            for i, file_name in enumerate(file_names[:available_slots]):
                pixmap = QPixmap(file_name).scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                slot_index = empty_slots[i]

                labels[slot_index].setPixmap(pixmap)
                labels[slot_index].setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.verify_faces()

    
    def verify_faces(self):
        backends = ["opencv", "ssd", "dlib", "mtcnn", "retinaface"]
        models = ["VGG-Face", "Facenet", "Facenet512", "OpenFace", "DeepFace", "DeepID", "ArcFace", "Dlib", "SFace"]

        if all(label.pixmap_image and not label.pixmap_image.isNull() for label in self.image_labels):
            try:
                temp_files = []
                results = []

                # save to temp folder
                for label in self.image_labels:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    label.pixmap_image.save(temp_file.name)
                    temp_files.append(temp_file.name)

                # verify images
                for i in range(len(temp_files) - 1):
                    for j in range(i + 1, len(temp_files)):
                        result = DeepFace.verify(
                            img1_path=temp_files[i],
                            img2_path=temp_files[j],
                            model_name=models[2],
                            detector_backend=backends[1],
                            threshold=0.6,
                            enforce_detection=False
                        )
                        results.append(result['verified'])

                if all(results):
                    self.face_verified = True
                    self.status_label.setText("Khuôn mặt khớp")
                    self.status_label.setStyleSheet("color: green; font-size: 14px;")
                else:
                    self.face_verified = False
                    self.status_label.setText("Khuôn mặt không khớp")
                    self.status_label.setStyleSheet("color: red; font-size: 14px;")

                for temp_file in temp_files:
                    os.remove(temp_file)

            except Exception as e:
                print("Error in face verification:", e)

    def save_and_exit(self):
        if not self.face_verified:
            QMessageBox.warning(self, "Lỗi", "Khuôn mặt không khớp, hãy thử lại.")
            return

        Session = sessionmaker(bind=self.engine)
        session = Session()

        # Truy vấn để lấy id (UUID) từ bảng user_details dựa trên Mã NV (employee_code)
        user_detail = session.query(user_details).filter_by(employee_code=self.employee_data['Mã NV']).first()

        if user_detail and user_detail.id:  # Kiểm tra nếu user_id tồn tại
            # Truy vấn user_images bằng user_id từ bảng user_details
            user_images_result = session.query(user_images).filter_by(user_id=user_detail.id).first()

            # Chuyển đổi ảnh thành base64
            base64_images = [label.convert_to_base64() for label in self.image_labels if not label.pixmap_image.isNull()]
            images_string = ','.join(base64_images) 

            for idx, base64_str in enumerate(base64_images):
                print(f"Ảnh {idx + 1}: {base64_str[:30]}...")  

            if user_images_result:
                # Cập nhật hình ảnh nếu đã có bản ghi, sử dụng phương thức ORM
                session.query(user_images).filter_by(user_id=user_detail.id).update({"images": images_string})
            else:
                # Tạo bản ghi mới nếu chưa có
                new_user_images = user_images.insert().values(user_id=user_detail.id, images=images_string)
                session.execute(new_user_images)

            # Commit thay đổi để lưu vào database
            session.commit()

            # Cập nhật trạng thái "Ảnh hiện tại" ngay lập tức sau khi lưu
            self.parent().update_image_status(user_detail.employee_code, len(base64_images) > 0)

        session.close()
        self.accept() 

# class for chup anh button
class CameraCaptureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_id = parent.employee_data['Mã NV'] 
        self.image_count = 0
        self.face_fully_inside = False
        self.parent_widget = parent 

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Chụp ảnh nhân sự')
        self.setGeometry(100, 100, 800, 600)

        # Create main layout
        self.layout = QVBoxLayout(self)

        # Create label to display video
        self.video_label = QLabel(self)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.video_label)

        # Create button to capture image
        self.capture_button = QPushButton('Chụp ảnh', self)
        self.capture_button.clicked.connect(self.capture_image)
        self.layout.addWidget(self.capture_button)

        # Initialize webcam
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(20)

        # Load Haar Cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        # Define oval size ratios
        self.oval_ratio_width = 0.35  
        self.oval_ratio_height = 0.7
        self.hidden_oval_scale = 0.9 

        # Instructions list
        self.instructions = ['Nhìn thẳng', 'Hướng phải 45 độ', 'Hướng trái 45 độ', 'Hướng trên 45 độ', 'Hướng dưới 45 độ']

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Flip the image horizontally (mirror effect)
            frame = cv2.flip(frame, 1)

            # Convert frame to grayscale for face detection
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Get the dimensions of the frame
            frame_height, frame_width = frame.shape[:2]

            # Define cropping dimensions (center crop)
            crop_width = min(frame_width, frame_height)  # Use the smaller dimension to create a square crop
            crop_x = (frame_width - crop_width) // 2
            crop_y = (frame_height - crop_width) // 2

            # Crop the image
            cropped_frame = frame[crop_y:crop_y + crop_width, crop_x:crop_x + crop_width]

            # Resize the cropped frame to fit the QLabel size
            resized_frame = cv2.resize(cropped_frame, (self.video_label.width(), self.video_label.height()), interpolation=cv2.INTER_AREA)

            # Perform face detection on the cropped grayscale image
            cropped_gray_frame = gray_frame[crop_y:crop_y + crop_width, crop_x:crop_x + crop_width]
            resized_gray_frame = cv2.resize(cropped_gray_frame, (self.video_label.width(), self.video_label.height()), interpolation=cv2.INTER_AREA)
            
            faces = self.face_cascade.detectMultiScale(resized_gray_frame, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))

            # Convert resized frame to RGB for display
            rgb_image = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

            # Set the QLabel to display the video frame
            self.video_label.setPixmap(QPixmap.fromImage(qt_image))

            # Draw oval and instructions
            self.draw_ovals_and_instructions(qt_image, faces)

    def draw_ovals_and_instructions(self, qt_image, faces):
        # Create a QPixmap to draw on
        pixmap = QPixmap.fromImage(qt_image)
        painter = QPainter(pixmap)

        # Get the actual size of the QLabel
        label_width = self.video_label.width()
        label_height = self.video_label.height()

        # Calculate dimensions for the visible oval (adjust for QLabel's dynamic size)
        oval_width = int(label_width * self.oval_ratio_width)
        oval_height = int(label_height * self.oval_ratio_height)

        # Center the oval within the QLabel
        oval_x = (label_width - oval_width) // 2
        oval_y = (label_height - oval_height) // 2

        # Calculate dimensions for the hidden oval (smaller than visible oval)
        hidden_oval_width = int(oval_width * self.hidden_oval_scale)
        hidden_oval_height = int(oval_height * self.hidden_oval_scale)
        hidden_oval_x = (label_width - hidden_oval_width) // 2
        hidden_oval_y = (label_height - hidden_oval_height) // 2

        # Set pen for drawing the visible oval
        pen = QPen(Qt.GlobalColor.red, 3, Qt.PenStyle.DashLine)

        # Check if any face is completely inside the hidden oval
        self.face_fully_inside = False
        for (x, y, w, h) in faces:
            # Adjust face position based on QLabel's dimensions
            face_center_x = x + w // 2
            face_center_y = y + h // 2

            # Check if the face is inside the hidden oval
            if (hidden_oval_x < face_center_x < hidden_oval_x + hidden_oval_width and
                hidden_oval_y < face_center_y < hidden_oval_y + hidden_oval_height):
                self.face_fully_inside = True
                break

        # Change visible oval color based on face position
        if self.face_fully_inside:
            pen.setColor(Qt.GlobalColor.green)
        else:
            pen.setColor(Qt.GlobalColor.red)

        painter.setPen(pen)
        painter.drawEllipse(oval_x, oval_y, oval_width, oval_height)

        # Draw instructions at the top of the oval
        self.draw_instructions(painter, oval_x, oval_y, oval_width, oval_height)

        # Finish painting and update label
        painter.end()
        self.video_label.setPixmap(pixmap)

    def draw_instructions(self, painter, oval_x, oval_y, oval_width, oval_height):
        instruction_text = self.instructions[self.image_count] if self.image_count < len(self.instructions) else ''
        painter.setPen(QPen(QColor('white')))
        painter.setBrush(QColor('black'))
        font = QFont('Arial', 16) 
        painter.setFont(font)

        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(instruction_text) + 20  # Add padding
        text_height = metrics.height() + 10  # Add padding

        # Draw instructions at the top of the oval
        text_rect = QRect(oval_x + (oval_width - text_width) // 2, oval_y - text_height - 10, text_width, text_height)
        painter.drawRect(text_rect)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, instruction_text)


    def is_face_fully_inside_oval(self, x, y, w, h, oval_x, oval_y, oval_width, oval_height):
        # Check if the entire face is within the oval bounds
        face_top_left_x = x
        face_top_left_y = y
        face_bottom_right_x = x + w
        face_bottom_right_y = y + h

        return (oval_x <= face_top_left_x <= oval_x + oval_width and
                oval_x <= face_bottom_right_x <= oval_x + oval_width and
                oval_y <= face_top_left_y <= oval_y + oval_height and
                oval_y <= face_bottom_right_y <= oval_y + oval_height)

    def capture_image(self):
        if not self.face_fully_inside:
            QMessageBox.warning(self, 'Warning', 'Vui lòng đảm bảo khuôn mặt nằm hoàn toàn trong vòng oval.')
            return

        ret, frame = self.cap.read()
        if ret:
            # Flash effect
            self.flash_effect()

            # Flip the image horizontally (mirror effect) before saving
            frame = cv2.flip(frame, 1)

            # Convert frame to QPixmap to display in the parent dialog
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            # Update the image frame in the parent widget
            self.parent_widget.add_image_to_frame(pixmap, self.image_count)

            # Update image count
            self.image_count += 1
            print(f'Ảnh {self.image_count} đã được chụp.')

            self.parent_widget.verify_faces()

            # Check if 5 images have been captured
            if self.image_count >= 5:
                self.show_completion_message()
                self.close() 

    def flash_effect(self):
        # Create a flash effect
        flash = QLabel(self)
        flash.setStyleSheet("background-color: white;")
        flash.setGeometry(0, 0, self.width(), self.height())
        flash.show()
        QTimer.singleShot(100, flash.close)

    def show_completion_message(self):
        # Show completion message
        msg = QMessageBox()
        msg.setWindowTitle('Thành công')
        msg.setText('Bạn đã chụp ảnh thành công.')
        msg.setStandardButtons(QMessageBox.StandardButton.Close)
        msg.buttonClicked.connect(self.close)
        msg.exec()

    def closeEvent(self, event):
        self.cap.release()
        super().closeEvent(event)

#class for main dashboard
class EmployeeDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = None  # DataFrame to store data
        self.engine = engine  # Database engine

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Danh sách nhân sự')
        self.setGeometry(100, 100, 1920, 1080)

        # Layouts
        self.main_layout = QVBoxLayout()
        self.top_layout = QHBoxLayout() 
        self.search_layout = QHBoxLayout()

        # Font settings for the buttons
        bold_font = QtGui.QFont()
        bold_font.setFamily("Arial")
        bold_font.setPointSize(14) 
        bold_font.setBold(True) 

        # "Màn hình chính" Button
        self.home_button = QPushButton('Màn hình chính', self)
        self.home_button.setFont(bold_font)  
        self.home_button.setFixedSize(200, 50)  
        self.home_button.clicked.connect(self.go_home)  # Connect to go_home method
        self.top_layout.addWidget(self.home_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # "Tải dữ liệu" Button
        self.upload_button = QPushButton('Tải dữ liệu', self)
        self.upload_button.setFont(bold_font) 
        self.upload_button.setFixedSize(200, 50) 
        self.upload_button.setStyleSheet("color: green;")
        self.upload_button.clicked.connect(self.upload_file)
        self.top_layout.addWidget(self.upload_button, alignment=Qt.AlignmentFlag.AlignRight)

        # Add the top layout to the main layout
        self.main_layout.addLayout(self.top_layout)

        # Search Fields
        self.search_id_input = QLineEdit(self)
        self.search_id_input.setPlaceholderText('Tìm mã NV')
        self.search_layout.addWidget(self.search_id_input)

        self.search_name_input = QLineEdit(self)
        self.search_name_input.setPlaceholderText('Tìm tên NV')
        self.search_layout.addWidget(self.search_name_input)

        # Table Widget
        self.table_widget = QTableWidget(self)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Set background color to white
        self.table_widget.setStyleSheet("QTableWidget { background-color: white; }")

        # Add search and table widgets to the layout
        self.main_layout.addLayout(self.search_layout)
        self.main_layout.addWidget(self.table_widget)

        self.setLayout(self.main_layout)

        # Connect search fields to filter function
        self.search_id_input.textChanged.connect(self.filter_table)
        self.search_name_input.textChanged.connect(self.filter_table)
    
    def go_home(self):
        from main import Ui_MainWindow  # Import the main window class
        self.main_window = QtWidgets.QMainWindow()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.main_window)
        self.main_window.showMaximized()
        self.close()

    def upload_file(self):
        try:
        # Fetch data using the fetch_employee_data function
            self.df = fetch_employee_data()
            if self.df.empty:
                raise ValueError("Không có dữ liệu để hiển thị")
            self.display_table(self.df)
        except Exception as e:
            self.show_error_message(f"Lỗi khi tải dữ liệu: {str(e)}")

        Session = sessionmaker(bind=self.engine)
        session = Session()
        # self.display_table(self.df)
        session.close()
    
    def show_error_message(self, message):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("Lỗi")
        error_dialog.setText("Dữ liệu không hoạt động")
        error_dialog.setInformativeText(message)
        error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        error_dialog.exec()

    def display_table(self, df):
        self.table_widget.setRowCount(len(df))
        self.table_widget.setColumnCount(len(df.columns))
        self.table_widget.setHorizontalHeaderLabels(df.columns)

        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)

        for i in range(len(df)):
            for j in range(len(df.columns)):
                if df.columns[j] == 'Ảnh hiện tại':
                    label = QLabel(df.iat[i, j])
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    if df.iat[i, j] == 'Đã có':
                        label.setStyleSheet("color: green;")
                    else:
                        label.setStyleSheet("color: red;")
                    self.table_widget.setCellWidget(i, j, label)
                elif df.columns[j] == 'Thiết lập':
                    # Add "Chỉnh sửa" và "Xóa NV" buttons
                    edit_button = QPushButton('Chỉnh sửa')
                    edit_button.setStyleSheet("background-color: blue; color: white;")
                    edit_button.setFixedSize(100, 20)
                    edit_button.clicked.connect(lambda _, row=i: self.show_password_dialog(self.edit_employee, row))

                    hbox = QHBoxLayout()
                    hbox.addWidget(edit_button)
                    hbox_widget = QWidget()
                    hbox_widget.setLayout(hbox)
                    self.table_widget.setCellWidget(i, j, hbox_widget)
                else:
                    item = QTableWidgetItem(str(df.iat[i, j]))
                    if df.columns[j] in ['Mã NV', 'Tên NV', 'Phòng ban', 'Xưởng']:
                        item.setForeground(QColor(Qt.GlobalColor.black))  # Set text color to black
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make non-editable
                    self.table_widget.setItem(i, j, item)

    def update_image_status(self, user_id, has_images):
        for row in range(self.df.shape[0]):
            if self.df.at[row, 'Mã NV'] == user_id:
                if has_images:
                    self.df.at[row, 'Ảnh hiện tại'] = 'Đã có'
                else:
                    self.df.at[row, 'Ảnh hiện tại'] = 'Chưa đủ 5 ảnh'
        self.display_table(self.df)

    def filter_table(self):
        if self.df is None:
            return

        id_filter = self.search_id_input.text().strip().lower()
        name_filter = self.search_name_input.text().strip().lower()

        filtered_df = self.df

        if id_filter:
            filtered_df = filtered_df[filtered_df['Mã NV'].astype(str).str.contains(id_filter, case=False, na=False)]
        if name_filter:
            filtered_df = filtered_df[filtered_df['Tên NV'].astype(str).str.contains(name_filter, case=False, na=False)]

        self.display_table(filtered_df)

    def edit_employee(self, row):
        if self.df is not None:
            employee_data = {
                'Mã NV': self.df.iloc[row]['Mã NV'],
                'Tên NV': self.df.iloc[row]['Tên NV'],
                'Phòng ban': self.df.iloc[row]['Phòng ban'],
                'Xưởng': self.df.iloc[row]['Xưởng']
            }

            dialog = EditEmployeeDialog(employee_data, self.engine, self)
            if dialog.exec():
                print("Thông tin đã được lưu.")

    def show_password_dialog(self, action, row):
        dialog = QDialog(self)
        dialog.setWindowTitle("Nhập mật khẩu")
        dialog.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        password_label = QLabel("Mật khẩu:")
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(password_label)
        layout.addWidget(password_input)
        
        button_layout = QHBoxLayout()
        confirm_button = QPushButton("Xác nhận")
        cancel_button = QPushButton("Hủy")
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        confirm_button.clicked.connect(lambda: self.check_password(password_input.text(), action, row, dialog))
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec()

    def check_password(self, password, action, row, dialog):
        if password == '@':
            dialog.accept()
            if row is not None:
                action(row)
            else:
                action()
        else:
            QMessageBox.warning(self, "Sai mật khẩu", "Mật khẩu không đúng.")
            dialog.reject()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EmployeeDashboard()
    ex.show()
    sys.exit(app.exec())