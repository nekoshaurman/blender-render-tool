import sqlite3
import json
from pathlib import Path
from src.models.project import Project, Settings


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = str(Path(db_path))
        # os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    unique_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    settings TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS thumbnails (
                    unique_id TEXT PRIMARY KEY,
                    thumbnail BLOB
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blender_paths (
                    path TEXT PRIMARY KEY,
                    version TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_project(self, project: Project):
        settings_json = json.dumps(project.settings.to_dict())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO projects (unique_id, name, file_path, settings)
                VALUES (?, ?, ?, ?)
            """, (project.unique_id, project.name, project.file_path, settings_json))
            conn.commit()

    def update_project(self, project: Project):
        settings_json = json.dumps(project.settings.to_dict())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE projects
                SET name = ?, file_path = ?, settings = ?
                WHERE unique_id = ?
            """, (project.name, project.file_path, settings_json, project.unique_id))
            conn.commit()

    def load_projects(self) -> list:
        projects = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT unique_id, name, file_path, settings FROM projects")
            for row in cursor.fetchall():
                unique_id, name, file_path, settings_json = row
                settings_dict = json.loads(settings_json)
                settings = Settings.from_dict(settings_dict)
                project = Project(unique_id=unique_id, name=name, file_path=file_path, settings=settings)
                projects.append(project)
        return projects

    def delete_project(self, unique_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE unique_id = ?", (unique_id,))
            conn.commit()

    def save_thumbnail(self, unique_id: str, thumbnail_data: bytes):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO thumbnails (unique_id, thumbnail)
                VALUES (?, ?)
            """, (unique_id, thumbnail_data))
            conn.commit()

    def get_thumbnail(self, unique_id: str) -> bytes:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT thumbnail FROM thumbnails WHERE unique_id = ?", (unique_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def delete_thumbnail(self, unique_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM thumbnails WHERE unique_id = ?", (unique_id,))
            conn.commit()

    def add_blender_path(self, path: str, version: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO blender_paths (path, version)
                VALUES (?, ?)
            """, (path, version))
            conn.commit()

    def get_blender_paths(self) -> dict:
        paths = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT path, version FROM blender_paths")
            for row in cursor.fetchall():
                paths[row[0]] = row[1]
        return paths
