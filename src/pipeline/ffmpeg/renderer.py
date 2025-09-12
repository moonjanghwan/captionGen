import os
import subprocess
import tempfile
from typing import List, Dict
import ffmpeg

class FFmpegRenderer:
    def __init__(self):
        self._check_ffmpeg_availability()

    def _check_ffmpeg_availability(self):
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except FileNotFoundError:
            raise FileNotFoundError("FFmpeg is not installed or not in the system's PATH.")

    def render_scene_video(self, audio_path: str, subtitle_frames: List[Dict], output_path: str, resolution: str, default_background: str):
        width, height = map(int, resolution.split('x'))
        
        total_duration = sum(f['duration'] for f in subtitle_frames)
        if total_duration == 0:
            print("Warning: Total duration is zero. Cannot render video.")
            return

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as concat_file:
            for frame in subtitle_frames:
                concat_file.write(f"file '{os.path.abspath(frame['output_path'])}'\n")
                concat_file.write(f"duration {frame['duration']}\n")
            # The last image needs to be specified again without duration
            if subtitle_frames:
                concat_file.write(f"file '{os.path.abspath(subtitle_frames[-1]['output_path'])}'\n")
            concat_list_path = concat_file.name

        try:
            background_input = ffmpeg.input(default_background, loop=1, t=total_duration).filter('scale', width, height)
            image_input = ffmpeg.input(concat_list_path, f='concat', safe=0, r='30')
            audio_input = ffmpeg.input(audio_path)

            video_stream = ffmpeg.overlay(background_input, image_input, x='(W-w)/2', y='(H-h)/2')

            (ffmpeg
                .output(video_stream, audio_input, output_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None)
                .run(overwrite_output=True, quiet=True))
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)

    def merge_videos(self, video_paths: List[str], output_path: str):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as concat_file:
            for path in video_paths:
                concat_file.write(f"file '{os.path.abspath(path)}'\n")
            concat_list_path = concat_file.name
        
        try:
            (ffmpeg
                .input(concat_list_path, f='concat', safe=0)
                .output(output_path, c='copy')
                .run(overwrite_output=True, quiet=True))
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)