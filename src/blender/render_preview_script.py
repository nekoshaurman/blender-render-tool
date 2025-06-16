import bpy
import sys
import os
import base64
from io import BytesIO
import tempfile
from pathlib import Path
import logging

log_dir = Path(__file__).parent
log_file = log_dir / "render_preview.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('RenderPreviewScript')

if __name__ == "__main__":
    try:
        file_path = sys.argv[5]
        unique_id = sys.argv[6]
        render_engine = sys.argv[7]
        cycles_denoising = int(sys.argv[8])
        cycles_device = sys.argv[9]
        threads = int(sys.argv[10])

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{file_path}' not found")

        logger.info(f"Opening file: {file_path}")
        bpy.ops.wm.open_mainfile(filepath=file_path)
        scene = bpy.context.scene

        logger.info("Setting render settings")
        scene.render.image_settings.file_format = 'PNG'
        scene.render.resolution_x = 512  # 512
        scene.render.resolution_y = 288  # 288
        scene.render.resolution_percentage = 100
        scene.render.threads = threads

        logger.info(f"Using render engine: {render_engine}")
        if render_engine == 'CYCLES':
            scene.render.engine = 'CYCLES'
            scene.cycles.samples = 16
            scene.cycles.use_denoising = bool(cycles_denoising)
            scene.cycles.device = cycles_device
        elif render_engine == 'EEVEE':
            scene.render.engine = 'BLENDER_EEVEE'
            scene.eevee.taa_render_samples = 16
        else:
            raise ValueError(f"Unsupported render engine: {render_engine}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "render.png"
            logger.info(f"Rendering to temporary file: {temp_path}")
            scene.render.filepath = str(temp_path)
            bpy.ops.render.render(write_still=True)
            logger.info("Render operation completed")

            if temp_path.exists():
                logger.info(f"Reading rendered file: {temp_path}")
                with open(temp_path, "rb") as f:
                    buffer = BytesIO(f.read())
                    buffer.seek(0)
                    thumbnail_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    logger.info("Encoding thumbnail data as base64")
                    print(f"data:image/png;base64,{thumbnail_data}", flush=True)
            else:
                raise FileNotFoundError(f"Rendered file not found at: {temp_path}")

        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"Cleaned up temporary file: {temp_path}")
        except Exception as e:
            logger.error(f"Failed to clean up temporary file: {str(e)}")

        logger.info("=============================================")

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        print(f"Error: {str(e)}", flush=True)
        sys.exit(1)
