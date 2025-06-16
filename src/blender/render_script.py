import bpy
import sys
import argparse
from pathlib import Path
import logging
import os

log_dir = Path(__file__).parent
log_file = log_dir / "render.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('RenderScript')


def setup_render_settings(settings):
    scene = bpy.context.scene
    render = scene.render

    render.resolution_x = int(settings["resolution_x"])
    render.resolution_y = int(settings["resolution_y"])
    render.resolution_percentage = int(settings["resolution_scale"])
    render.fps = int(settings["fps"])
    render.fps_base = float(settings["fps_base"])
    render.image_settings.file_format = settings["format"]

    output_path = Path(settings["output"])
    if settings["filename"]:
        output_path = output_path.parent / settings["filename"]
    os.makedirs(output_path.parent, exist_ok=True)
    render.filepath = str(output_path)

    if settings["engine"] == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = int(settings["samples"])
        scene.cycles.use_denoising = bool(int(settings["denoising"]))
        scene.cycles.device = settings["device"]
        render.threads = int(settings["threads"])
    else:
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = int(settings["samples"])


def render_image(frame, settings):
    scene = bpy.context.scene
    scene.frame_current = frame
    setup_render_settings(settings)
    logger.info(f"Рендеринг кадра {frame} в {settings['output']}")
    bpy.ops.render.render(write_still=True)


def render_animation(start, end, step, settings):
    scene = bpy.context.scene
    scene.frame_start = start
    scene.frame_end = end
    scene.frame_step = step
    setup_render_settings(settings)
    logger.info(f"Рендеринг анимации с {start} по {end} с шагом {step} в {settings['output']}")
    bpy.ops.render.render(animation=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["image", "animation"])
    parser.add_argument("--frame", type=int)
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    parser.add_argument("--step", type=int)
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", required=True)
    parser.add_argument("--engine", required=True)
    parser.add_argument("--samples", required=True)
    parser.add_argument("--denoising", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--threads", required=True)
    parser.add_argument("--resolution_x", required=True)
    parser.add_argument("--resolution_y", required=True)
    parser.add_argument("--resolution_scale", required=True)
    parser.add_argument("--fps", required=True)
    parser.add_argument("--fps_base", required=True)
    parser.add_argument("--filename", required=True)
    parser.add_argument("project_path", help="Path to .blend file")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

    settings = {
        "resolution_x": args.resolution_x,
        "resolution_y": args.resolution_y,
        "resolution_scale": args.resolution_scale,
        "fps": args.fps,
        "fps_base": args.fps_base,
        "output": args.output,
        "format": args.format,
        "engine": args.engine,
        "samples": args.samples,
        "denoising": args.denoising,
        "device": args.device,
        "threads": args.threads,
        "filename": args.filename
    }

    bpy.ops.wm.open_mainfile(filepath=args.project_path)

    if args.type == "image":
        render_image(args.frame, settings)
    else:
        render_animation(args.start, args.end, args.step, settings)


if __name__ == "__main__":
    main()
