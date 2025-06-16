import psutil
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QLabel, QGroupBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QLineEdit, QTextEdit, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
from src.models.project import Project, Settings
from src.blender.blender_manager import BlenderManager
from pathlib import Path
import os


class ProjectBlockWidget(QWidget):
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        name_label = QLabel(f"Name: {project.name}")
        name_label.setStyleSheet("font-weight: bold;")
        path_label = QLabel(f"Path: {project.file_path}")
        path_label.setWordWrap(True)
        layout.addWidget(name_label)
        layout.addWidget(path_label)
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.animation_group = None
        self.db_manager = db_manager
        self.blender_manager = BlenderManager(self, self.db_manager.get_blender_paths())
        self.projects = []
        self.current_project = None
        self.setWindowTitle("Blender Render Tool")
        self.setMinimumSize(1600, 900)
        self.init_ui()
        self.load_projects()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Project")
        remove_button = QPushButton("Remove Project")
        move_up_button = QPushButton("Move Up")
        move_down_button = QPushButton("Move Down")
        render_queue_button = QPushButton("Render Queue")  # Новая кнопка
        add_button.clicked.connect(self.add_project)
        remove_button.clicked.connect(self.remove_project)
        move_up_button.clicked.connect(self.move_up)
        move_down_button.clicked.connect(self.move_down)
        render_queue_button.clicked.connect(self.render_queue)
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(move_up_button)
        button_layout.addWidget(move_down_button)
        button_layout.addWidget(render_queue_button)
        left_layout.addLayout(button_layout)

        self.project_list = QListWidget()
        self.project_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.project_list.itemClicked.connect(self.select_project)
        left_layout.addWidget(self.project_list)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Logs")
        left_layout.addWidget(self.log_output)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        sidebar_layout = QVBoxLayout(scroll_widget)

        self.sidebar = QGroupBox()
        sidebar_content_layout = QVBoxLayout()

        blender_group = QGroupBox()
        blender_layout = QVBoxLayout()
        blender_path_layout = QHBoxLayout()
        blender_path_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.blender_path_combo = QComboBox()
        self.blender_path_combo.addItems(self.db_manager.get_blender_paths().keys())
        self.blender_path_combo.currentTextChanged.connect(self.update_blender_version_label)
        self.blender_path_combo.setFixedWidth(400)

        add_blender_button = QPushButton("Add Blender Path")
        add_blender_button.setFixedWidth(120)
        add_blender_button.clicked.connect(self.add_blender_path)

        blender_path_layout.addWidget(self.blender_path_combo)
        blender_path_layout.addWidget(add_blender_button)

        self.blender_version_label = QLabel("Version: Unknown")

        blender_layout.addLayout(blender_path_layout)
        blender_layout.addWidget(self.blender_version_label)

        blender_group.setLayout(blender_layout)
        sidebar_content_layout.addWidget(blender_group)

        preview_group = QGroupBox()
        preview_layout = QVBoxLayout()
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)

        self.preview_label = QLabel("No preview available")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedSize(512, 288)

        self.render_preview_button = QPushButton("Render Preview")
        self.render_preview_button.clicked.connect(self.render_preview)

        preview_layout.addWidget(self.preview_label)
        preview_layout.addWidget(self.render_preview_button)

        preview_group.setLayout(preview_layout)
        sidebar_content_layout.addWidget(preview_group)

        settings_group = QGroupBox()
        settings_layout = QVBoxLayout()
        settings_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)

        render_engine_layout = QHBoxLayout()
        render_engine_label = QLabel("Render Engine:")
        render_engine_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.render_engine = QComboBox()
        self.render_engine.addItems(["CYCLES", "EEVEE"])
        self.render_engine.currentTextChanged.connect(self.update_render_engine)

        render_engine_layout.addWidget(render_engine_label)
        render_engine_layout.addWidget(self.render_engine)
        settings_layout.addLayout(render_engine_layout)

        self.cycles_group = QGroupBox()
        cycles_layout = QVBoxLayout()
        cycles_denoising_layout = QHBoxLayout()
        cycles_denoising_label = QLabel("Denoising:")
        cycles_denoising_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.cycles_denoising = QCheckBox()

        cycles_denoising_layout.addWidget(cycles_denoising_label)
        cycles_denoising_layout.addWidget(self.cycles_denoising)
        cycles_layout.addLayout(cycles_denoising_layout)

        cycles_device_layout = QHBoxLayout()
        cycles_device_label = QLabel("Device:")
        cycles_device_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.cycles_device = QComboBox()
        self.cycles_device.addItems(["CPU", "GPU"])
        self.cycles_device.currentTextChanged.connect(self.update_cycles_device)

        cycles_device_layout.addWidget(cycles_device_label)
        cycles_device_layout.addWidget(self.cycles_device)
        cycles_layout.addLayout(cycles_device_layout)

        cycles_threads_layout = QHBoxLayout()
        self.cycles_threads_label = QLabel("Threads (Max: %d):" % (psutil.cpu_count(logical=True) or 1))
        self.cycles_threads_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.cycles_threads = QSpinBox()
        self.cycles_threads.setRange(0, psutil.cpu_count(logical=True) or 1)
        self.cycles_threads.setValue(psutil.cpu_count(logical=True) or 1)

        cycles_threads_layout.addWidget(self.cycles_threads_label)
        cycles_threads_layout.addWidget(self.cycles_threads)
        cycles_layout.addLayout(cycles_threads_layout)

        cycles_samples_layout = QHBoxLayout()
        cycles_samples_label = QLabel("Samples:")
        cycles_samples_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.cycles_samples = QSpinBox()
        self.cycles_samples.setRange(1, 4096)

        cycles_samples_layout.addWidget(cycles_samples_label)
        cycles_samples_layout.addWidget(self.cycles_samples)
        cycles_layout.addLayout(cycles_samples_layout)

        self.cycles_group.setLayout(cycles_layout)
        settings_layout.addWidget(self.cycles_group)

        self.eevee_group = QGroupBox()
        eevee_layout = QVBoxLayout()

        eevee_samples_layout = QHBoxLayout()
        eevee_samples_label = QLabel("Samples:")
        eevee_samples_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.eevee_samples = QSpinBox()
        self.eevee_samples.setRange(1, 256)

        eevee_samples_layout.addWidget(eevee_samples_label)
        eevee_samples_layout.addWidget(self.eevee_samples)
        eevee_layout.addLayout(eevee_samples_layout)

        self.eevee_group.setLayout(eevee_layout)
        settings_layout.addWidget(self.eevee_group)

        resolution_group = QGroupBox()
        resolution_layout = QVBoxLayout()

        res_x_layout = QHBoxLayout()
        res_x_label = QLabel("X:")
        res_x_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.resolution_x = QSpinBox()
        self.resolution_x.setRange(4, 65536)

        res_x_layout.addWidget(res_x_label)
        res_x_layout.addWidget(self.resolution_x)

        res_y_layout = QHBoxLayout()
        res_y_label = QLabel("Y:")
        res_y_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.resolution_y = QSpinBox()
        self.resolution_y.setRange(4, 65536)

        res_y_layout.addWidget(res_y_label)
        res_y_layout.addWidget(self.resolution_y)

        scale_layout = QHBoxLayout()
        scale_label = QLabel("%:")
        scale_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.resolution_scale = QSpinBox()
        self.resolution_scale.setRange(1, 32767)

        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(self.resolution_scale)

        resolution_layout.addLayout(res_x_layout)
        resolution_layout.addLayout(res_y_layout)
        resolution_layout.addLayout(scale_layout)
        resolution_group.setLayout(resolution_layout)
        settings_layout.addWidget(resolution_group)

        render_type_layout = QHBoxLayout()
        render_type_label = QLabel("Render Type:")
        render_type_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.render_type = QComboBox()
        self.render_type.addItems(["Image", "Animation"])
        self.render_type.currentTextChanged.connect(self.update_render_type)

        render_type_layout.addWidget(render_type_label)
        render_type_layout.addWidget(self.render_type)
        settings_layout.addLayout(render_type_layout)

        self.animation_group = QGroupBox()
        animation_layout = QVBoxLayout()

        self.frame_start_layout = QHBoxLayout()
        frame_start_label = QLabel("Start Frame:")
        frame_start_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.frame_start = QSpinBox()
        self.frame_start.setRange(0, 1048574)

        self.frame_start_layout.addWidget(frame_start_label)
        self.frame_start_layout.addWidget(self.frame_start)

        self.frame_end_layout = QHBoxLayout()
        frame_end_label = QLabel("End Frame:")
        frame_end_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.frame_end = QSpinBox()
        self.frame_end.setRange(0, 1048574)

        self.frame_end_layout.addWidget(frame_end_label)
        self.frame_end_layout.addWidget(self.frame_end)

        self.frame_step_layout = QHBoxLayout()
        frame_step_label = QLabel("Step:")
        frame_step_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.frame_step = QSpinBox()
        self.frame_step.setRange(1, 1048574)

        self.frame_step_layout.addWidget(frame_step_label)
        self.frame_step_layout.addWidget(self.frame_step)

        fps_value_layout = QHBoxLayout()
        fps_value_label = QLabel("FPS:")
        fps_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.fps_value = QSpinBox()
        self.fps_value.setRange(1, 32767)

        fps_value_layout.addWidget(fps_value_label)
        fps_value_layout.addWidget(self.fps_value)

        fps_base_layout = QHBoxLayout()
        fps_base_label = QLabel("FPS Base:")
        fps_base_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.fps_base = QDoubleSpinBox()
        self.fps_base.setRange(0.0001, 1000000)
        self.fps_base.setSingleStep(0.1)

        fps_base_layout.addWidget(fps_base_label)
        fps_base_layout.addWidget(self.fps_base)

        animation_layout.addLayout(self.frame_start_layout)
        animation_layout.addLayout(self.frame_end_layout)
        animation_layout.addLayout(self.frame_step_layout)
        animation_layout.addLayout(fps_value_layout)
        animation_layout.addLayout(fps_base_layout)
        self.animation_group.setLayout(animation_layout)
        settings_layout.addWidget(self.animation_group)

        self.image_group = QGroupBox()
        image_layout = QVBoxLayout()

        self.frame_current_layout = QHBoxLayout()
        frame_current_label = QLabel("Current Frame:")
        frame_current_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.frame_current = QSpinBox()
        self.frame_current.setRange(0, 1048574)

        self.frame_current_layout.addWidget(frame_current_label)
        self.frame_current_layout.addWidget(self.frame_current)

        image_layout.addLayout(self.frame_current_layout)
        self.image_group.setLayout(image_layout)
        settings_layout.addWidget(self.image_group)

        output_group = QGroupBox()
        output_layout = QVBoxLayout()
        file_format_layout = QHBoxLayout()
        file_format_label = QLabel("File Format:")
        file_format_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.file_format = QComboBox()
        self.file_format.addItems(["PNG", "JPEG", "EXR"])

        file_format_layout.addWidget(file_format_label)
        file_format_layout.addWidget(self.file_format)

        output_path_layout = QHBoxLayout()
        output_path_input_layout = QHBoxLayout()
        output_path_label = QLabel("Output Path:")
        output_path_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)

        output_path_button = QPushButton("...")
        output_path_button.setFixedWidth(30)
        output_path_button.clicked.connect(self.select_output_path)

        output_path_layout.addWidget(output_path_label, stretch=1)
        output_path_input_layout.addWidget(self.output_path, stretch=2)
        output_path_input_layout.addWidget(output_path_button)
        output_path_layout.addLayout(output_path_input_layout, stretch=1)

        output_filename_layout = QHBoxLayout()
        output_filename_label = QLabel("Output Filename:")
        output_filename_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.output_filename = QLineEdit()

        output_filename_layout.addWidget(output_filename_label, stretch=1)
        output_filename_layout.addWidget(self.output_filename, stretch=1)

        output_layout.addLayout(file_format_layout)
        output_layout.addLayout(output_path_layout)
        output_layout.addLayout(output_filename_layout)
        output_group.setLayout(output_layout)
        settings_layout.addWidget(output_group)

        button_layout = QHBoxLayout()
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        render_button = QPushButton("Render Project")
        render_button.clicked.connect(self.render_project)
        button_layout.addWidget(save_button)
        button_layout.addWidget(render_button)
        settings_layout.addLayout(button_layout)

        settings_group.setLayout(settings_layout)
        sidebar_content_layout.addWidget(settings_group)

        #sidebar_content_layout.addLayout(settings_layout)
        self.sidebar.setLayout(sidebar_content_layout)
        sidebar_layout.addWidget(self.sidebar)

        scroll_area.setWidget(scroll_widget)
        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(scroll_area, 1)

        self.update_render_type()

    def save_thumbnail(self, unique_id, thumbnail_data):
        if thumbnail_data:
            self.db_manager.save_thumbnail(unique_id, thumbnail_data)
            self.log(f"Миниатюра сохранена для проекта: {unique_id}")
            if self.current_project and self.current_project.unique_id == unique_id:
                image = QImage.fromData(thumbnail_data)
                pixmap = QPixmap.fromImage(image)
                self.preview_label.setPixmap(pixmap.scaled(
                    self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                self.log("Миниатюра обновлена в интерфейсе")
        else:
            self.log(f"Не удалось сохранить миниатюру для проекта: {unique_id}")

    def update_render_engine(self):
        if self.render_engine.currentText() == "CYCLES":
            self.cycles_group.setVisible(True)
            self.eevee_group.setVisible(False)
        else:
            self.cycles_group.setVisible(False)
            self.eevee_group.setVisible(True)

    def update_cycles_device(self):
        if self.cycles_device.currentText() == "CPU":
            self.cycles_threads_label.setVisible(True)
            self.cycles_threads.setVisible(True)
        else:
            self.cycles_threads_label.setVisible(False)
            self.cycles_threads.setVisible(False)

    def update_render_type(self):
        render_type = self.render_type.currentText()
        if render_type == "Image":
            self.image_group.setVisible(True)
            self.animation_group.setVisible(False)
            self.file_format.clear()
            self.file_format.addItems(["PNG", "JPEG", "EXR"])
        else:
            self.image_group.setVisible(False)
            self.animation_group.setVisible(True)
            self.file_format.clear()
            self.file_format.addItems(["AVI_JPEG", "AVI_RAW", "FFMPEG"])

    def select_output_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку вывода")
        if folder:
            self.output_path.setText(str(Path(folder)))
            self.log("Выбран путь вывода: " + folder)

    def add_blender_path(self):
        filters = "Executables (*.exe);;All Files (*)" if os.name == "nt" else "All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите исполняемый файл Blender", "", filters
        )
        if file_path:
            version = self.blender_manager.get_blender_version(file_path)
            self.db_manager.add_blender_path(file_path, version)
            self.blender_manager.blender_paths = self.db_manager.get_blender_paths()
            self.blender_path_combo.clear()
            self.blender_path_combo.addItems(self.db_manager.get_blender_paths().keys())
            self.blender_path_combo.setCurrentText(file_path)
            self.blender_version_label.setText(f"Версия: {version}")
            self.log(f"Добавлен путь Blender: {file_path} (Версия: {version})")

    def update_blender_version_label(self):
        blender_path = self.blender_path_combo.currentText()
        if blender_path:
            version = self.blender_manager.get_blender_version(blender_path)
            self.blender_version_label.setText(f"Версия: {version}")
            self.log(f"Выбран путь Blender: {blender_path} (Версия: {version})")
        else:
            self.blender_version_label.setText("Версия: Неизвестно")
            self.log("Путь Blender не выбран")

    def render_preview(self):
        if not self.current_project:
            self.log("Проект не выбран")
            return
        if not self.current_project.settings.blender_path:
            self.log("Путь Blender не задан для проекта")
            return
        self.blender_manager.render_project_thumbnail(self.current_project, self.update_preview)
        self.log(f"Рендеринг миниатюры для: {self.current_project.name}")

    def update_preview(self, unique_id, thumbnail_data):
        if thumbnail_data and self.current_project:
            if self.current_project.unique_id == unique_id:
                image = QImage.fromData(thumbnail_data)
                pixmap = QPixmap.fromImage(image)
                self.preview_label.setPixmap(pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                self.log("Миниатюра обновлена и сохранена в базе данных")
            else:
                self.log("Рендеринг миниатюры не удался или проект изменился")

    def render_project(self):
        if not self.current_project:
            self.log("Проект не выбран")
            return
        if not self.current_project.settings.blender_path:
            self.log("Путь Blender не задан для проекта")
            return
        if not self.current_project.settings.output_path:
            self.log("Путь вывода не задан")
            return
        self.save_settings()
        self.blender_manager.render_project(self.current_project, self.log)
        self.log(f"Рендеринг начат для проекта: {self.current_project.name}")

    def render_queue(self):
        if not self.projects:
            self.log("Очередь проектов пуста")
            return
        self.log("Начало рендера очереди проектов")
        for project in self.projects:
            if not project.settings.blender_path:
                self.log(f"Пропуск проекта {project.name}: путь Blender не задан")
                continue
            if not project.settings.output_path:
                self.log(f"Пропуск проекта {project.name}: путь вывода не задан")
                continue
            self.current_project = project
            self.save_settings()
            self.blender_manager.render_project(project, self.log)
            self.log(f"Рендеринг начат для проекта: {project.name}")
        self.log("Рендер очереди завершен")

    def save_settings(self):
        if not self.current_project:
            self.log("Проект не выбран")
            return
        try:
            settings = Settings(
                resolution_x=self.resolution_x.value(),
                resolution_y=self.resolution_y.value(),
                resolution_scale=self.resolution_scale.value(),
                fps=self.fps_value.value(),
                fps_base=self.fps_base.value(),
                frame_start=self.frame_start.value(),
                frame_end=self.frame_end.value(),
                frame_step=self.frame_step.value(),
                frame_current=self.frame_current.value(),
                render_engine=self.render_engine.currentText(),
                render_type=self.render_type.currentText(),
                cycles_samples=self.cycles_samples.value(),
                cycles_denoising=self.cycles_denoising.isChecked(),
                cycles_device=self.cycles_device.currentText(),
                threads=self.cycles_threads.value(),
                eevee_samples=self.eevee_samples.value(),
                file_format=self.file_format.currentText(),
                file_formats_image=["PNG", "JPEG", "EXR"],
                file_formats_movie=["AVI_JPEG", "AVI_RAW", "FFMPEG"],
                output_path=self.output_path.text(),
                output_filename=self.output_filename.text() or self.current_project.name,  # Используем имя проекта по умолчанию
                blender_path=self.blender_path_combo.currentText()
            )
            self.current_project.settings = settings
            self.db_manager.update_project(self.current_project)
            self.log(f"Настройки сохранены для проекта: {self.current_project.name}")
        except ValueError as e:
            self.log(f"Ошибка сохранения настроек: {str(e)}")

    def log(self, message):
        self.log_output.append(message)
        self.log_output.ensureCursorVisible()

    def add_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Добавить файл Blender", "", "Blender Files (*.blend)"
        )
        if file_path:
            settings = self.blender_manager.get_settings_from_project(file_path)
            if not settings:
                settings = Settings(
                    output_path=str(Path(file_path).parent / "output"),
                    output_filename=Path(file_path).stem,  # Устанавливаем имя файла по умолчанию
                    blender_path=list(self.db_manager.get_blender_paths().keys())[0] if self.db_manager.get_blender_paths() else ""
                )
                self.log("Не удалось загрузить настройки, используются значения по умолчанию")
            else:
                settings = Settings(**settings)
                if not settings.output_filename:
                    settings.output_filename = Path(file_path).stem  # Устанавливаем имя файла по умолчанию
                self.log("Настройки загружены из файла .blend")
            project = Project(
                unique_id="",
                name="",
                file_path=str(Path(file_path)),
                settings=settings
            )
            self.projects.append(project)
            self.db_manager.save_project(project)
            self.update_project_list()
            self.log(f"Добавлен проект: {project.name}")

    def remove_project(self):
        selected_row = self.project_list.currentRow()
        if selected_row >= 0:
            project = self.projects.pop(selected_row)
            self.db_manager.delete_project(project.unique_id)
            self.db_manager.delete_thumbnail(project.unique_id)
            self.update_project_list()
            if self.current_project == project:
                self.current_project = None
                self.sidebar.setVisible(False)
            self.log(f"Удален проект: {project.name}")

    def move_up(self):
        selected_row = self.project_list.currentRow()
        if selected_row > 0:
            self.projects[selected_row], self.projects[selected_row - 1] = (
                self.projects[selected_row - 1], self.projects[selected_row]
            )
            self.update_project_list()
            self.project_list.setCurrentRow(selected_row - 1)
            self.log("Проект перемещен вверх")

    def move_down(self):
        selected_row = self.project_list.currentRow()
        if selected_row < len(self.projects) - 1 and selected_row >= 0:
            self.projects[selected_row], self.projects[selected_row + 1] = (
                self.projects[selected_row + 1], self.projects[selected_row]
            )
            self.update_project_list()
            self.project_list.setCurrentRow(selected_row + 1)
            self.log("Проект перемещен вниз")

    def select_project(self, item: QListWidgetItem):
        project_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_project = next((p for p in self.projects if p.unique_id == project_id), None)
        if self.current_project:
            self.sidebar.setVisible(True)
            self.update_settings_ui()
            thumbnail = self.db_manager.get_thumbnail(self.current_project.unique_id)
            if thumbnail:
                image = QImage.fromData(thumbnail)
                pixmap = QPixmap.fromImage(image)
                self.preview_label.setPixmap(pixmap.scaled(
                    self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                self.log("Загружена существующая миниатюра из базы данных")
            else:
                self.preview_label.setText("Превью недоступно")
            self.log(f"Выбран проект: {self.current_project.name}")

    def update_settings_ui(self):
        if not self.current_project:
            return
        settings = self.current_project.settings
        self.render_type.setCurrentText(settings.render_type)
        self.render_engine.setCurrentText(settings.render_engine)
        self.resolution_x.setValue(settings.resolution_x)
        self.resolution_y.setValue(settings.resolution_y)
        self.resolution_scale.setValue(settings.resolution_scale)
        self.frame_start.setValue(settings.frame_start)
        self.frame_end.setValue(settings.frame_end)
        self.frame_step.setValue(settings.frame_step)
        self.frame_current.setValue(settings.frame_current)
        self.fps_value.setValue(settings.fps)
        self.fps_base.setValue(settings.fps_base)
        self.cycles_samples.setValue(settings.cycles_samples)
        self.cycles_denoising.setChecked(settings.cycles_denoising)
        self.cycles_device.setCurrentText(settings.cycles_device)
        self.cycles_threads.setValue(settings.threads)
        self.eevee_samples.setValue(settings.eevee_samples)
        self.file_format.setCurrentText(settings.file_format)
        self.output_path.setText(settings.output_path)
        self.output_filename.setText(settings.output_filename)
        self.blender_path_combo.setCurrentText(settings.blender_path)
        blender_path = settings.blender_path
        if blender_path:
            version = self.blender_manager.get_blender_version(blender_path)
            self.blender_version_label.setText(f"Version: {version}")
        else:
            self.blender_version_label.setText("Version: unknown")
        self.update_render_engine()
        self.update_cycles_device()
        self.update_render_type()

    def update_project_list(self):
        self.project_list.clear()
        for project in self.projects:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, project.unique_id)
            block_widget = ProjectBlockWidget(project)
            item.setSizeHint(block_widget.sizeHint())
            self.project_list.addItem(item)
            self.project_list.setItemWidget(item, block_widget)

    def load_projects(self):
        self.projects = self.db_manager.load_projects()
        self.update_project_list()

    def log(self, message):
        self.log_output.append(message)
        self.log_output.ensureCursorVisible()
