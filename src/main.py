import os
import sys

from PyQt6 import QtGui
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.database.db_manager import DatabaseManager
from src.logger_config import setup_logger

logger = setup_logger('Main')


def apply_stylesheet(app):
    # Load and apply stylesheet
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        qss_path = os.path.join(base_dir, 'ui', 'styles', 'blender_style.qss')
        with open(qss_path, 'r') as f:
            app.setStyleSheet(f.read())
            logger.info("Style sheet imported")
    except FileNotFoundError:
        logger.warning("style.qss not found, using default styling")
    except Exception as e:
        logger.error(f"Failed to load stylesheet: {str(e)}")


def main():
    logger.info("Starting Blender Render Tool")

    app = QApplication(sys.argv)

    apply_stylesheet(app)

    app.setStyle('Fusion')

    app.setFont(QtGui.QFont("Blender Mono I18n", 10))

    db_manager = DatabaseManager("blender_render_tool.db")

    window = MainWindow(db_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
