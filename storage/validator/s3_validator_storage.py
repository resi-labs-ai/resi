import pandas as pd
import os
import pyarrow as pa
import pyarrow.parquet as pq
import threading
import bittensor as bt

class S3ValidationStorage:
    def __init__(self, storage_path):
        self.file_path = storage_path
        # Ensure directory exists
        dir_path = os.path.dirname(self.file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        self._ensure_file_exists()
        self._write_lock = threading.Lock()

    def _ensure_file_exists(self):
        if not os.path.exists(self.file_path):
            self._create_empty_dataframe()

    def _create_empty_dataframe(self):
        df = pd.DataFrame(columns=['hotkey', 'job_count', 'block'])
        self._write_parquet_internal(df)

    def _write_parquet_internal(self, df):
        """Internal write method without locking. Caller must hold lock."""
        temp_file = f"{self.file_path}.temp"
        try:
            dir_path = os.path.dirname(self.file_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            table = pa.Table.from_pandas(df)
            pq.write_table(table, temp_file)
            if not os.path.exists(temp_file):
                raise FileNotFoundError(f"Temp file was not created: {temp_file}")
            os.replace(temp_file, self.file_path)
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise e

    def _safe_read_parquet(self):
        try:
            return pd.read_parquet(self.file_path)
        except Exception as e:
            bt.logging.error(f"Error reading Parquet file: {e}")
            bt.logging.info("Attempting to recover data...")
            return self._recover_data()

    def _recover_data(self):
        try:
            table = pq.read_table(self.file_path)
            return table.to_pandas()
        except Exception as e:
            bt.logging.error(f"Recovery failed: {e}")
            bt.logging.warning("Creating a new empty dataframe.")
            return pd.DataFrame(columns=['hotkey', 'job_count', 'block'])

    def get_validation_info(self, hotkey):
        with self._write_lock:
            df = self._safe_read_parquet()
            matching_rows = df[df['hotkey'] == hotkey]
            return matching_rows.to_dict('records')[0] if not matching_rows.empty else None

    def update_validation_info(self, hotkey, job_count, block):
        with self._write_lock:
            df = self._safe_read_parquet()
            new_row = pd.DataFrame({'hotkey': [hotkey], 'job_count': [job_count], 'block': [block]})
            df = pd.concat([df[df['hotkey'] != hotkey], new_row], ignore_index=True)
            self._write_parquet_internal(df)

    def get_all_validations(self):
        with self._write_lock:
            return self._safe_read_parquet()