import sqlite3


class DataBase:
    def __init__(self, db_name='python_tasks.db'):
        self.db_name = db_name
        self.create_table()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def create_table(self):
        with self.get_connection() as conn:
            conn.execute("""
                        CREATE TABLE IF NOT EXISTS python_tasks
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         task TEXT NOT NULL,
                         section TEXT NOT NULL,
                         subsection TEXT NOT NULL)
                         """)
            conn.commit()

    def show_table(self, section=None, subsection=None):
        with self.get_connection() as conn:
            sql = 'SELECT task FROM python_tasks'
            params = []
            conditions = []

            if section:
                conditions.append('section = ?')
                params.append(section)
            if subsection:
                conditions.append('subsection = ?')
                params.append(subsection)
            cursor = conn.execute(sql)

            if conditions:
                sql += ' WHERE ' + ' AND '.join(conditions)
                cursor = conn.execute(sql, params)

            return cursor.fetchall()
