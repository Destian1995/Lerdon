import sqlite3

class DBManager:
    _instance = None

    def __new__(cls, db_path=None):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance.conn = sqlite3.connect(db_path, check_same_thread=False)
            cls._instance.conn.execute("PRAGMA journal_mode=WAL;")
            cls._instance.conn.execute("PRAGMA synchronous=NORMAL;")
            cls._instance.conn.execute("PRAGMA busy_timeout=5000;")
        return cls._instance

    def get_connection(self):
        return self._instance.conn

    def close_all(self):
        if self._instance.conn:
            self._instance.conn.execute("PRAGMA wal_checkpoint(FULL);")
            self._instance.conn.execute("PRAGMA journal_mode=DELETE;")
            self._instance.conn.close()