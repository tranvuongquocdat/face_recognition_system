import threading
import subprocess
import sys
from PyQt6 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        # Khởi tạo các cờ để kiểm soát việc chạy luồng
        self.checkin_thread_running = False
        self.checkout_thread_running = False

        MainWindow.setObjectName("MainWindow")
        MainWindow.showMaximized()  # Mở cửa sổ ở chế độ toàn màn hình

        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # Layout chính
        self.main_layout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.main_layout.setObjectName("main_layout")

        # Spacer ở trên để đẩy các nút xuống giữa
        self.top_spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.main_layout.addItem(self.top_spacer)

        self.label = QtWidgets.QLabel(parent=self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Bahnschrift SemiBold")
        font.setPointSize(30)  # Tăng kích thước font
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setObjectName("label")
        # Đặt chiều cao tối thiểu để đảm bảo đủ không gian
        self.label.setMinimumHeight(100)
        self.main_layout.addWidget(self.label)

        # Spacer để tạo khoảng cách giữa label và các nút bên dưới
        self.middle_spacer = QtWidgets.QSpacerItem(20, 150, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self.main_layout.addItem(self.middle_spacer)

        # Tạo layout để chứa các nút
        self.button_layout = QtWidgets.QVBoxLayout()
        self.button_layout.setObjectName("button_layout")

        # Nút "Hệ thống điểm danh khuôn mặt"
        self.face_attendace_checking = QtWidgets.QPushButton(parent=self.centralwidget)
        self.face_attendace_checking.setFixedSize(600, 100)  # Đặt kích thước cố định lớn hơn
        font = QtGui.QFont()
        font.setFamily("Bahnschrift SemiBold")
        font.setPointSize(20)
        self.face_attendace_checking.setFont(font)
        self.face_attendace_checking.setObjectName("face_attendace_checking")
        self.button_layout.addWidget(self.face_attendace_checking, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        # Spacer giữa nút 1 và nút 2
        self.button_layout.addItem(QtWidgets.QSpacerItem(30, 30, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed))

        # Nút "Danh sách nhân sự"
        self.danh_sach_nhan_su = QtWidgets.QPushButton(parent=self.centralwidget)
        self.danh_sach_nhan_su.setFixedSize(600, 100)  # Đặt kích thước cố định lớn hơn
        font.setPointSize(20)
        self.danh_sach_nhan_su.setFont(font)
        self.danh_sach_nhan_su.setObjectName("danh_sach_nhan_su")
        self.button_layout.addWidget(self.danh_sach_nhan_su, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        # Spacer giữa nút 2 và nút 3
        self.button_layout.addItem(QtWidgets.QSpacerItem(30, 30, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed))

        # Nút "Lịch sử điểm danh"
        self.lich_su_diem_danh = QtWidgets.QPushButton(parent=self.centralwidget)
        self.lich_su_diem_danh.setFixedSize(600, 100)  # Đặt kích thước cố định lớn hơn
        font.setPointSize(20)
        self.lich_su_diem_danh.setFont(font)
        self.lich_su_diem_danh.setObjectName("lich_su_diem_danh")
        self.button_layout.addWidget(self.lich_su_diem_danh, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        # Thêm button_layout vào main_layout
        self.main_layout.addLayout(self.button_layout)

        # Spacer ở dưới để căn giữa các nút
        self.bottom_spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.main_layout.addItem(self.bottom_spacer)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # Kết nối sự kiện click với phương thức self.open_ui2_window
        self.face_attendace_checking.clicked.connect(self.open_attendance_checking_window)
        self.danh_sach_nhan_su.clicked.connect(self.open_employee_dashboard)
        self.lich_su_diem_danh.clicked.connect(self.open_tracking_history_window)

        # Lưu tham chiếu tới MainWindow để có thể đóng sau này
        self.main_window = MainWindow

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.face_attendace_checking.setText(_translate("MainWindow", "Hệ thống điểm danh khuôn mặt"))
        self.danh_sach_nhan_su.setText(_translate("MainWindow", "Danh sách nhân sự"))
        self.lich_su_diem_danh.setText(_translate("MainWindow", "Lịch sử điểm danh"))
        self.label.setText(_translate("MainWindow", "HỆ THỐNG ĐIỂM DANH NHÂN SỰ SỬ DỤNG NHẬN DIỆN KHUÔN MẶT"))

    def run_script(self, script_name):
        """
        Chạy file Python trong một luồng riêng, với xử lý ngoại lệ.
        """
        try:
            subprocess.Popen([sys.executable, script_name])
            print(f"Khởi chạy {script_name} thành công.")
        except Exception as e:
            print(f"Lỗi khi khởi chạy {script_name}: {e}")

    def open_attendance_checking_window(self):
        from attendance_tracking_in import AttendanceCheckingWindow  # Import the EmployeeDashboard class
        self.window = QtWidgets.QMainWindow()
        self.ui = AttendanceCheckingWindow()
        self.ui.setupUi(self.window)
        self.window.showFullScreen()  # Hiển thị cửa sổ ở chế độ toàn màn hình
        self.main_window.close()

    def open_employee_dashboard(self):
        from employee_dashboard_new import EmployeeDashboard  # Import the EmployeeDashboard class
        self.window = QtWidgets.QMainWindow()
        self.ui = EmployeeDashboard()
        self.ui.showMaximized()  # Show the dashboard in full screen
        self.main_window.close()

    def open_tracking_history_window(self):
        from tracking_history_local_db import Ui_MainWindow as TrackingHistoryWindow  # Import lớp giao diện tracking history
        self.window = QtWidgets.QMainWindow()
        self.ui = TrackingHistoryWindow()
        self.ui.setupUi(self.window)
        self.window.showMaximized()  # Hiển thị cửa sổ ở chế độ toàn màn hình
        self.main_window.close()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.showFullScreen()  # Mở cửa sổ ở chế độ toàn màn hình
    sys.exit(app.exec())
