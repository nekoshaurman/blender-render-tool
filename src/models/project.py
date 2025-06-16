import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import psutil

@dataclass
class Settings:
    """Модель настроек рендера Blender."""
    resolution_x: int = 1920
    resolution_y: int = 1080
    resolution_scale: int = 100
    fps: int = 24
    fps_base: float = 1.0
    frame_start: int = 1
    frame_end: int = 250
    frame_step: int = 1
    frame_current: int = 1
    render_engine: str = "CYCLES"
    render_type: str = "Image"
    cycles_samples: int = 128
    cycles_denoising: bool = False
    cycles_device: str = "CPU"
    threads: int = 0  # 0 означает автоопределение
    eevee_samples: int = 64
    file_format: str = "PNG"
    file_formats_image: list = None
    file_formats_movie: list = None
    output_path: str = ""
    output_filename: str = ""  # Новое поле для имени выходного файла
    blender_path: str = ""

    def __post_init__(self):
        self.file_formats_image = self.file_formats_image or ["PNG", "JPEG", "EXR"]
        self.file_formats_movie = self.file_formats_movie or ["AVI_JPEG", "AVI_RAW", "FFMPEG"]
        if self.render_engine not in ["CYCLES", "EEVEE"]:
            raise ValueError("Only 'CYCLES' or 'EEVEE'")
        if self.render_type not in ["Image", "Animation"]:
            raise ValueError("Render type error")
        max_samples = 4096 if self.render_engine == "CYCLES" else 256
        if not (1 <= self.cycles_samples <= max_samples):
            raise ValueError(f"Count of Cycles samples from 1 to {max_samples}")
        if not (1 <= self.eevee_samples <= 256):
            raise ValueError("Count of EEVEE samples from 1 to 256")
        if self.file_format not in self.file_formats_image + self.file_formats_movie:
            raise ValueError(f"Invalid file format: {self.file_format}")
        if self.output_path:
            self.output_path = str(Path(self.output_path))
        if self.blender_path:
            self.blender_path = str(Path(self.blender_path))
        # Автоопределение количества ядер, если threads равно 0 или недопустимо
        max_threads = psutil.cpu_count(logical=True) or 1
        if self.threads <= 0 or self.threads > max_threads:
            self.threads = max_threads
        elif self.threads > max_threads:
            raise ValueError(f"Max count of threads: {max_threads}")

    def to_dict(self) -> Dict:
        """Преобразование настроек в словарь для сериализации."""
        return {
            "resolution_x": self.resolution_x,
            "resolution_y": self.resolution_y,
            "resolution_scale": self.resolution_scale,
            "fps": self.fps,
            "fps_base": self.fps_base,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "frame_step": self.frame_step,
            "frame_current": self.frame_current,
            "render_engine": self.render_engine,
            "render_type": self.render_type,
            "cycles_samples": self.cycles_samples,
            "cycles_denoising": self.cycles_denoising,
            "cycles_device": self.cycles_device,
            "threads": self.threads,
            "eevee_samples": self.eevee_samples,
            "file_format": self.file_format,
            "file_formats_image": self.file_formats_image,
            "file_formats_movie": self.file_formats_movie,
            "output_path": self.output_path,
            "output_filename": self.output_filename,  # Добавляем output_filename
            "blender_path": self.blender_path
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Settings":
        """Создание экземпляра Settings из словаря."""
        return cls(**data)

@dataclass
class Project:
    """Project model for Blender Render Tool."""
    unique_id: str
    name: str
    file_path: str
    settings: Settings
    preview_path: str = ""

    def __post_init__(self):
        self.file_path = str(Path(self.file_path))
        if not self.name:
            self.name = os.path.basename(self.file_path)
        if not self.unique_id:
            self.unique_id = str(uuid.uuid4())
        if not isinstance(self.settings, Settings):
            self.settings = Settings.from_dict(self.settings)
