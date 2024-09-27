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

logging.basicConfig(level=logging.DEBUG)

def load_config():
    with open("config_in.yaml", "r") as config_file:
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

def sync_database():
    from sqlalchemy import create_engine, MetaData, Table
    import pandas as pd
    import uuid
    import json

    # Database connection URI for PostgreSQL
    pg_database_uri = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
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