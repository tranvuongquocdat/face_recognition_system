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


def base64_to_pixmap(base64_str):
    image_data = base64.b64decode(base64_str)
    image = QImage.fromData(image_data)
    return QPixmap.fromImage(image).scaled(
        260, 200, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation
    )

def qimage_to_numpy(qimage):
    # Convert QImage to byte array
    qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
    width = qimage.width()
    height = qimage.height()

    ptr = qimage.bits()
    ptr.setsize(height * width * 3)  # 3 bytes per pixel for RGB format
    arr = np.array(ptr).reshape(height, width, 3)  # Convert to a numpy array and reshape
    return arr