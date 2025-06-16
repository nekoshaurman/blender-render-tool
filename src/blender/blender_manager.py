import subprocess
import sys
import threading
import os
import bpy
import shutil
import re
import base64

import psutil
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
from src.logger_config import setup_logger

logger = setup_logger('BlenderManager')

class BlenderManager(QObject):
    thumbnail_ready = pyqtSignal(str, bytes)
    render_complete = pyqtSignal(str, bool, str)  # unique_id, success, message

    def __init__(self, parent=None, blender_paths=None):
        super().__init__(parent)
        self.parent = parent
        self.blender_paths = blender_paths or {}
        self.blender_executable = self.find_blender_executable()
        if parent:
            self.thumbnail_ready.connect(parent.save_thumbnail)

    def find_blender_executable(self):
        if os.name == 'nt':
            blender_exec = "blender.exe"
        elif sys.platform == 'darwin':
            blender_exec = "Blender"
            mac_paths = [
                "/Applications/Blender.app/Contents/MacOS/Blender",
                str(Path.home() / "Applications/Blender.app/Contents/MacOS/Blender")
            ]
            for path in mac_paths:
                if os.path.exists(path):
                    logger.info(f"Найден исполняемый файл Blender: {path}")
                    if self.parent and hasattr(self.parent, 'db_manager'):
                        version = self.get_blender_version(path)
                        self.parent.db_manager.add_blender_path(path, version)
                    return path
        else:
            blender_exec = "blender"

        path = shutil.which(blender_exec)
        if path:
            logger.info(f"Найден исполняемый файл Blender в PATH: {path}")
            if self.parent and hasattr(self.parent, 'db_manager'):
                version = self.get_blender_version(path)
                self.parent.db_manager.add_blender_path(path, version)
            return path

        for path in self.blender_paths.keys():
            if os.path.exists(path):
                logger.info(f"Найден исполняемый файл Blender из базы данных: {path}")
                return path

        logger.error("Исполняемый файл Blender не найден")
        return None

    def set_blender_path(self, path):
        if os.path.exists(path):
            self.blender_executable = path
            logger.info(f"Set Blender executable to: {path}")
        else:
            logger.error(f"Invalid Blender path: {path}")
            if self.parent:
                self.parent.log(f"Invalid Blender path: {path}")

    def get_blender_version(self, blender_path=None):
        blender_path = blender_path or self.blender_executable
        if not blender_path or not os.path.exists(blender_path):
            return "Unknown"
        if blender_path in self.blender_paths:
            return self.blender_paths[blender_path]
        try:
            result = subprocess.run(
                [blender_path, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            version = re.search(r"Blender (\d+\.\d+\.\d+)", result.stdout)
            return version.group(1) if version else "Unknown"
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to get Blender version: {str(e)}")
            return "Unknown"

    def get_settings_from_project(self, file_path: str) -> dict:
        if not os.path.exists(file_path):
            logger.error(f"Файл проекта не найден: {file_path}")
            return None
        try:
            bpy.ops.wm.open_mainfile(filepath=file_path)
            scene = bpy.context.scene
            max_threads = psutil.cpu_count(logical=True) or 1
            settings = {
                "resolution_x": scene.render.resolution_x,
                "resolution_y": scene.render.resolution_y,
                "resolution_scale": scene.render.resolution_percentage,
                "fps": scene.render.fps,
                "fps_base": scene.render.fps_base,
                "frame_start": scene.frame_start,
                "frame_end": scene.frame_end,
                "frame_step": scene.frame_step,
                "frame_current": scene.frame_current,
                "render_engine": "EEVEE" if scene.render.engine in ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"] else "CYCLES",
                "render_type": "Image" if scene.render.image_settings.file_format in ["PNG", "JPEG", "EXR"] else "Animation",
                "cycles_samples": scene.cycles.samples if hasattr(scene, 'cycles') else 128,
                "cycles_denoising": scene.cycles.use_denoising if hasattr(scene, 'cycles') else False,
                "cycles_device": scene.cycles.device if hasattr(scene, 'cycles') else "CPU",
                "threads": min(scene.render.threads, max_threads) if hasattr(scene.render, 'threads') else max_threads,
                "eevee_samples": scene.eevee.taa_render_samples if hasattr(scene, 'eevee') else 64,
                "file_format": scene.render.image_settings.file_format,
                "file_formats_image": ["PNG", "JPEG", "EXR"],
                "file_formats_movie": ["AVI_JPEG", "AVI_RAW", "FFMPEG"],
                "output_path": scene.render.filepath or str(Path(file_path).parent / "output"),
                "output_filename": Path(file_path).stem,  # Устанавливаем имя файла по умолчанию
                "blender_path": self.blender_executable or ""
            }
            logger.info(f"Получены настройки для проекта: {file_path}")
            return settings
        except Exception as e:
            logger.error(f"Ошибка получения настроек: {str(e)}")
            return None

    def render_project_thumbnail(self, project, callback):
        if not project:
            logger.error("Invalid project")
            if self.parent:
                self.parent.log("Error: Invalid project")
            callback(project.unique_id, None)
            return

        blender_path = project.settings.blender_path or self.blender_executable
        if not blender_path or not os.path.exists(blender_path):
            logger.error(f"Blender executable not found for project: {project.file_path}")
            if self.parent:
                self.parent.log("Error: Blender not found for project")
            callback(project.unique_id, None)
            return

        logger.info(f"Starting thumbnail render for: {project.file_path} with Blender: {blender_path}")
        if self.parent:
            self.parent.log(f"Start render thumbnail: {project.file_path} with Blender: {blender_path}")

        script_path = str(Path(__file__).parent / "render_preview_script.py")
        if not os.path.exists(script_path):
            logger.error(f"Render script not found: {script_path}")
            if self.parent:
                self.parent.log("Render script not found")
            callback(project.unique_id, None)
            return

        settings = project.settings.to_dict()
        command = [
            str(blender_path),
            "--background",
            "--python", str(script_path),
            "--",
            str(project.file_path),
            project.unique_id,
            settings["render_engine"],
            str(int(settings["cycles_denoising"])),
            settings["cycles_device"],
            str(settings["threads"])
        ]

        def run_render():
            try:
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info(f"Thumbnail render completed for: {project.file_path}")
                output = process.stdout.strip()

                data_line = None
                for line in output.splitlines():
                    if line.startswith("data:image/png;base64,"):
                        data_line = line
                        break

                if data_line:
                    thumbnail_data = base64.b64decode(data_line.split(",", 1)[1])
                    logger.info(f"Successfully processed thumbnail for: {project.unique_id}")
                    self.thumbnail_ready.emit(project.unique_id, thumbnail_data)
                    callback(project.unique_id, thumbnail_data)
                else:
                    logger.error(f"No valid thumbnail data found in output: {output}")
                    callback(project.unique_id, None)
            except subprocess.CalledProcessError as e:
                logger.error(f"Thumbnail render failed with code {e.returncode}: {e.stderr}")
                if self.parent:
                    self.parent.log(f"Thumbnail render failed: {e.stderr}")
                callback(project.unique_id, None)
            except Exception as e:
                logger.error(f"Unexpected error in thumbnail render: {str(e)}")
                if self.parent:
                    self.parent.log(f"Thumbnail render error: {str(e)}")
                callback(project.unique_id, None)

        threading.Thread(target=run_render).start()

    def render_project(self, project, log_callback):
        if not project.settings.blender_path or not os.path.exists(project.settings.blender_path):
            log_callback("Путь к исполняемому файлу Blender не указан или недоступен")
            return
        script_path = Path(__file__).parent / "render_script.py"
        if not script_path.exists():
            log_callback(f"Скрипт рендеринга не найден: {script_path}")
            return

        blender_path = project.settings.blender_path
        settings = project.settings.to_dict()
        settings["project_path"] = str(project.file_path)
        settings["unique_id"] = project.unique_id

        output_path = Path(settings["output_path"])
        if settings["output_filename"]:
            output_path = output_path / settings["output_filename"]

        command = [
            str(blender_path),
            "--background",
            "--python", str(script_path),
            "--"
        ]
        if project.settings.render_type == "Image":
            command.extend([
                "--type", "image",
                "--frame", str(project.settings.frame_current),
                "--output", str(output_path),
                "--format", project.settings.file_format
            ])
        else:
            command.extend([
                "--type", "animation",
                "--start", str(project.settings.frame_start),
                "--end", str(project.settings.frame_end),
                "--step", str(project.settings.frame_step),
                "--output", str(output_path),
                "--format", project.settings.file_format
            ])
        command.extend([
            "--engine", project.settings.render_engine,
            "--samples", str(project.settings.cycles_samples if project.settings.render_engine == "CYCLES" else project.settings.eevee_samples),
            "--denoising", str(int(project.settings.cycles_denoising)),
            "--device", project.settings.cycles_device,
            "--threads", str(project.settings.threads),
            "--resolution_x", str(project.settings.resolution_x),
            "--resolution_y", str(project.settings.resolution_y),
            "--resolution_scale", str(project.settings.resolution_scale),
            "--fps", str(project.settings.fps),
            "--fps_base", str(project.settings.fps_base),
            "--filename", settings["output_filename"],
            str(project.file_path)
        ])

        def run_render():
            try:
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info(f"Render completed for project: {project.name}")
                log_callback(f"Рендеринг завершен для проекта: {project.name}")
                self.render_complete.emit(project.unique_id, True, "Рендеринг успешно завершен")
            except subprocess.CalledProcessError as e:
                logger.error(f"Render failed with code {e.returncode}: {e.stderr}")
                log_callback(f"Ошибка рендеринга проекта {project.name}: {e.stderr}")
                self.render_complete.emit(project.unique_id, False, f"Ошибка: {e.stderr}")
            except Exception as e:
                logger.error(f"Unexpected error in render: {str(e)}")
                log_callback(f"Ошибка рендеринга проекта {project.name}: {str(e)}")
                self.render_complete.emit(project.unique_id, False, f"Ошибка: {str(e)}")

        threading.Thread(target=run_render).start()
