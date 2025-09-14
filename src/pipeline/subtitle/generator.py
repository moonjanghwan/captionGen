import os
import re
import json
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from PIL import Image, ImageDraw

from .text_renderer import TextRenderer

@dataclass
class SubtitleFrame:
    """자막 프레임 정보"""
    frame_number: int
    start_time: float
    end_time: float
    duration: float
    scene_id: str
    text: str
    output_path: str

class SubtitleGenerator:
    def __init__(self, settings: Dict[str, Any], identifier: str, log_callback=None):
        self.text_renderer = TextRenderer(settings)
        self.identifier = identifier
        self.log_callback = log_callback
        self.frames: List[SubtitleFrame] = []
        self.output_dir = ""
        self.resolution = (1920, 1080)

    def _log(self, message):
        if self.log_callback:
            self.log_callback(message, "INFO")
        else:
            print(message)

    def generate_from_manifest(self, manifest_data: Dict[str, Any], output_dir: str, script_type: str, fps: int = 30) -> List[SubtitleFrame]:
        self.output_dir = output_dir
        self.resolution = self._parse_resolution(manifest_data.get("resolution", "1920x1080"))
        
        scenes = manifest_data.get("scenes", [])
        frame_counter = 0
        
        for scene in scenes:
            scene_type = scene.get("type", "")
            
            scene_output_dir = os.path.join(self.output_dir, self.identifier, "dialog" if scene_type == "conversation" else scene_type)
            os.makedirs(scene_output_dir, exist_ok=True)

            if scene_type == "intro":
                frames = self._generate_intro_frames(scene, frame_counter, fps, scene_output_dir)
                self.frames.extend(frames)
                frame_counter += len(frames)
            elif scene_type == "ending":
                frames = self._generate_ending_frames(scene, frame_counter, fps, scene_output_dir)
                self.frames.extend(frames)
                frame_counter += len(frames)
            elif scene_type == "dialogue":
                frames = self._generate_dialogue_frames(scene, frame_counter, fps, scene_output_dir)
                self.frames.extend(frames)
                frame_counter += len(frames)
            elif scene_type == "conversation":
                frames = self._generate_conversation_frames(scene, frame_counter, fps, scene_output_dir)
                self.frames.extend(frames)
                frame_counter += len(frames)

        # Add thumbnail generation here, assuming it's not part of the manifest scenes directly
        # self.generate_thumbnail_frames(...) # This will be added later

        self._save_frame_info(script_type)
        return self.frames

    def _parse_resolution(self, resolution_str: str) -> Tuple[int, int]:
        try:
            width, height = map(int, resolution_str.split('x'))
            return width, height
        except:
            return (1920, 1080)

    def _create_base_image(self) -> Image.Image:
        width, height = self.resolution
        common_settings = self.text_renderer.config.get("common", {})
        bg_settings = common_settings.get("bg", {})
        bg_type = bg_settings.get("type", "색상")
        bg_value = bg_settings.get("value", "#000000")
        bg_alpha = float(bg_settings.get("alpha", 1.0))

        if bg_type == "색상":
            from PIL import Image, ImageColor
            try:
                rgb = ImageColor.getrgb(bg_value)
            except:
                rgb = (0, 0, 0)
            return Image.new("RGBA", (width, height), (rgb[0], rgb[1], rgb[2], int(bg_alpha * 255)))
        elif bg_type == "이미지" and bg_value and os.path.isfile(bg_value):
            from PIL import Image
            img = Image.open(bg_value).convert('RGBA')
            iw, ih = img.size
            scale = max(width / max(1, iw), height / max(1, ih))
            new_w, new_h = int(iw * scale), int(ih * scale)
            img = img.resize((new_w, new_h))
            left = max(0, (new_w - width) // 2)
            top = max(0, (new_h - height) // 2)
            img = img.crop((left, top, left + width, top + height))
            img.putalpha(int(bg_alpha * 255))
            return img
        else:
            return Image.new("RGBA", (width, height), (0, 0, 0, 0))

    def _generate_intro_frames(self, scene: Dict[str, Any], start_frame: int, fps: int, scene_output_dir: str) -> List[SubtitleFrame]:
        self._log(f"Generating frames for scene: {scene.get('id')}")
        full_script = scene.get("full_script", "")
        
        frames = []
        if not full_script.strip():
            return frames

        image = Image.new("RGBA", self.resolution, (0, 0, 0, 0))
        
        # Get settings for intro/ending
        settings_key = f"{scene.get('type')} 설정"
        text_settings = self.text_renderer.config.get("tabs", {}).get(settings_key, {})
        row_settings = text_settings.get("rows", [{}])[0]

        font_name = row_settings.get("폰트(pt)", "KoPubWorld돋움체")
        font_size = int(row_settings.get("크기(pt)", 48))
        font_color = row_settings.get("색상", "#FFFFFF")
        max_width = int(row_settings.get("w", self.resolution[0] - 100))
        align = row_settings.get("좌우 정렬", "center").lower()
        vertical_align = row_settings.get("상하 정렬", "top").lower()
        position = (int(row_settings.get("x", self.resolution[0] // 2)), int(row_settings.get("y", 50)))

        common_settings = self.text_renderer.config.get("common", {})
        border_settings = common_settings.get("border", {})
        shadow_settings = common_settings.get("shadow", {})

        # Render the entire script onto a single image
        self.text_renderer.render_text_to_image(
            image=image,
            text=full_script,
            position=position,
            font_name=font_name,
            font_size=font_size,
            font_color=font_color,
            max_width=max_width,
            align=align,
            vertical_align=vertical_align,
            stroke_width=int(border_settings.get("thick", 0)),
            stroke_color=border_settings.get("color", "#000000"),
            shadow_offset=(int(shadow_settings.get("offx", 0)), int(shadow_settings.get("offy", 0))),
            shadow_color=shadow_settings.get("color", "#000000")
        )
        
        output_path = os.path.join(scene_output_dir, f"{self.identifier}_{start_frame:04d}.png")
        self.text_renderer.save_image(image, output_path)
        
        # Estimate duration for the entire script
        duration = self._estimate_speech_duration(full_script) 

        frame = SubtitleFrame(
            frame_number=start_frame,
            start_time=start_frame / fps,
            end_time=(start_frame + duration * fps) / fps,
            duration=duration,
            scene_id=scene.get("id"),
            text=full_script,
            output_path=output_path
        )
        frames.append(frame)
        return frames

    def _generate_ending_frames(self, scene: Dict[str, Any], start_frame: int, fps: int, scene_output_dir: str) -> List[SubtitleFrame]:
        self._log(f"--- Generating ending frame for scene: {scene.get('id')} ---")
        self._log(f"Scene data: {scene}")
        settings_key = f"{scene.get('type')} 설정"
        text_settings = self.text_renderer.config.get("tabs", {}).get(settings_key, {})
        self._log(f"Text settings: {text_settings}")
        row_settings = text_settings.get("rows", [{}])[0]
        self._log(f"Row settings: {row_settings}")

        font_name = row_settings.get("폰트(pt)", "KoPubWorld돋움체")
        font_size = int(row_settings.get("크기(pt)", 48))
        font_color = row_settings.get("색상", "#FFFFFF")
        max_width = int(row_settings.get("w", self.resolution[0] - 100))
        align = row_settings.get("좌우 정렬", "center").lower()
        vertical_align = row_settings.get("상하 정렬", "top").lower()
        position = (int(row_settings.get("x", self.resolution[0] // 2)), int(row_settings.get("y", 50)))

        # Smart line breaking
        font = self.text_renderer._get_font(font_name, font_size)
        wrapped_text = self.text_renderer._smart_wrap(full_script, font, max_width)
        self._log(f"Smart wrapped text: {wrapped_text}")

        common_settings = self.text_renderer.config.get("common", {})
        border_settings = common_settings.get("border", {})
        shadow_settings = common_settings.get("shadow", {})

        self._log(f"Rendering ending with settings: position={position}, font_name={font_name}, font_size={font_size}, font_color={font_color}, max_width={max_width}, align={align}, vertical_align={vertical_align}, stroke_width={border_settings.get('thick', 0)}, stroke_color={border_settings.get('color', '#000000')}, shadow_offset={(int(shadow_settings.get('offx', 0)), int(shadow_settings.get('offy', 0)))}, shadow_color={shadow_settings.get('color', '#000000')}")

        # Render the entire script onto a single image
        self.text_renderer.render_text_to_image(
            image=image,
            text=wrapped_text,
            position=position,
            font_name=font_name,
            font_size=font_size,
            font_color=font_color,
            max_width=max_width,
            align=align,
            vertical_align=vertical_align,
            stroke_width=int(border_settings.get("thick", 0)),
            stroke_color=border_settings.get("color", "#000000"),
            shadow_offset=(int(shadow_settings.get("offx", 0)), int(shadow_settings.get("offy", 0))),
            shadow_color=shadow_settings.get("color", "#000000")
        )
        
        output_path = os.path.join(scene_output_dir, f"{self.identifier}_{start_frame:04d}.png")
        self.text_renderer.save_image(image, output_path)
        
        # Estimate duration for the entire script
        duration = self._estimate_speech_duration(full_script) 

        frame = SubtitleFrame(
            frame_number=start_frame,
            start_time=start_frame / fps,
            end_time=(start_frame + duration * fps) / fps,
            duration=duration,
            scene_id=scene.get("id"),
            text=full_script,
            output_path=output_path
        )
        frames.append(frame)
        return frames

    def _generate_dialogue_frames(self, scene: Dict[str, Any], start_frame: int, fps: int, scene_output_dir: str) -> List[SubtitleFrame]:
        self._log(f"Generating dialogue frames for scene: {scene.get('id')}")
        script = scene.get("content", {}).get("script", [])
        frames = []
        
        text_settings = self.text_renderer.config.get("tabs", {}).get("대화 설정", {})
        font_name = text_settings.get("폰트(pt)", "KoPubWorld돋움체")
        font_size = int(text_settings.get("크기(pt)", 48))
        font_color = text_settings.get("색상", "#FFFFFF")
        max_width = self.resolution[0] - 100
        align = text_settings.get("정렬", "left")
        vertical_align = text_settings.get("수직정렬", "top")
        position = (50, 50) # Example position

        for i, item in enumerate(script):
            text = f"{item.get('speaker', '')}: {item.get('text', '')}"
            duration = self._estimate_speech_duration(text)
            image = Image.new("RGBA", self.resolution, (0, 0, 0, 0))
            
            self.text_renderer.render_text_to_image(
                image=image,
                text=text,
                position=position,
                font_name=font_name,
                font_size=font_size,
                font_color=font_color,
                max_width=max_width,
                align=align,
                vertical_align=vertical_align
            )
            
            output_path = os.path.join(scene_output_dir, f"{self.identifier}_{start_frame + i:04d}.png")
            self.text_renderer.save_image(image, output_path)
            
            frame = SubtitleFrame(
                frame_number=start_frame + i,
                start_time=(start_frame + i) / fps,
                end_time=(start_frame + i + duration * fps) / fps,
                duration=duration,
                scene_id=scene.get("id"),
                text=text,
                output_path=output_path
            )
            frames.append(frame)
        return frames

    def _generate_conversation_frames(self, scene: Dict[str, Any], start_frame: int, fps: int, scene_output_dir: str) -> List[SubtitleFrame]:
        self._log(f"Generating conversation frames for scene: {scene.get('id')}")
        content = scene.get("content", {})
        frames = []
        
        text_settings = self.text_renderer.config.get("tabs", {}).get("회화 설정", {})
        font_name = text_settings.get("폰트(pt)", "KoPubWorld돋움체")
        font_size = int(text_settings.get("크기(pt)", 48))
        font_color = text_settings.get("색상", "#FFFFFF")
        max_width = self.resolution[0] - 100
        align = text_settings.get("정렬", "center")
        vertical_align = text_settings.get("수직정렬", "center") # Conversation might be centered

        # Screen 1
        text1 = f"{content.get('order', '')}\n{content.get('native_script', '')}"
        duration1 = self._estimate_speech_duration(content.get('native_script', ''))
        image1 = Image.new("RGBA", self.resolution, (0, 0, 0, 0))
        
        self.text_renderer.render_text_to_image(
            image=image1,
            text=text1,
            position=(self.resolution[0] // 2, self.resolution[1] // 2), # Center of the screen
            font_name=font_name,
            font_size=font_size,
            font_color=font_color,
            max_width=max_width,
            align=align,
            vertical_align=vertical_align
        )
        
        output_path1 = os.path.join(scene_output_dir, f"{self.identifier}_{start_frame:04d}.png")
        self.text_renderer.save_image(image1, output_path1)
        frame1 = SubtitleFrame(
            frame_number=start_frame,
            start_time=start_frame / fps,
            end_time=(start_frame + duration1 * fps) / fps,
            duration=duration1,
            scene_id=scene.get("id"),
            text=text1,
            output_path=output_path1
        )
        frames.append(frame1)

        # Screen 2
        text2 = (f"{content.get('order', '')}\n"
                 f"{content.get('native_script', '')}\n"
                 f"{content.get('learning_script', '')}\n"
                 f"{content.get('reading_script', '')}")
        duration2 = self._estimate_speech_duration(content.get('learning_script', ''))
        image2 = Image.new("RGBA", self.resolution, (0, 0, 0, 0))
        
        self.text_renderer.render_text_to_image(
            image=image2,
            text=text2,
            position=(self.resolution[0] // 2, self.resolution[1] // 2), # Center of the screen
            font_name=font_name,
            font_size=font_size,
            font_color=font_color,
            max_width=max_width,
            align=align,
            vertical_align=vertical_align
        )
        
        output_path2 = os.path.join(scene_output_dir, f"{self.identifier}_{start_frame + 1:04d}.png")
        self.text_renderer.save_image(image2, output_path2)
        frame2 = SubtitleFrame(
            frame_number=start_frame + 1,
            start_time=(start_frame + 1) / fps,
            end_time=(start_frame + 1 + duration2 * fps) / fps,
            duration=duration2,
            scene_id=scene.get("id"),
            text=text2,
            output_path=output_path2
        )
        frames.append(frame2)

        return frames

    def generate_thumbnail_frames(self, project_name: str, identifier: str, output_dir: str, thumbnail_settings: Dict[str, Any]) -> List[SubtitleFrame]:
        self._log(f"Generating thumbnail frames for project: {project_name}")
        
        thumbnail_output_dir = os.path.join(output_dir, identifier, "thumbnail")
        os.makedirs(thumbnail_output_dir, exist_ok=True)

        # Assuming AI generated JSON file path
        ai_json_path = os.path.join(output_dir, identifier, f"{identifier}_ai.json")
        thumbnail_texts = []

        try:
            with open(ai_json_path, 'r', encoding='utf-8') as f:
                ai_data = json.load(f)
                # Assuming the structure of ai_data contains a list of thumbnail suggestions
                # Each suggestion is a dictionary with a 'text' key
                if 'thumbnail_suggestions' in ai_data:
                    for suggestion in ai_data['thumbnail_suggestions']:
                        if 'text' in suggestion:
                            thumbnail_texts.append(suggestion['text'])
                elif 'thumbnail' in ai_data and isinstance(ai_data['thumbnail'], list):
                    # Alternative structure if 'thumbnail' is a list of strings
                    thumbnail_texts.extend(ai_data['thumbnail'])
                elif 'thumbnail_text' in ai_data and isinstance(ai_data['thumbnail_text'], list):
                    # Another alternative structure
                    thumbnail_texts.extend(ai_data['thumbnail_text'])
                else:
                    self._log(f"⚠️ AI JSON 파일에서 썸네일 텍스트를 찾을 수 없습니다: {ai_json_path}")

        except FileNotFoundError:
            self._log(f"❌ AI JSON 파일을 찾을 수 없습니다: {ai_json_path}")
            return []
        except json.JSONDecodeError:
            self._log(f"❌ AI JSON 파일 디코딩 오류: {ai_json_path}")
            return []

        frames = []
        frame_counter = 0
        
        # Use thumbnail_settings for font, color, etc.
        font_name = thumbnail_settings.get("폰트(pt)", "KoPubWorld돋움체")
        font_size = int(thumbnail_settings.get("크기(pt)", 72)) # Larger default for thumbnails
        font_color = thumbnail_settings.get("색상", "#FFFFFF")
        max_width = self.resolution[0] - 200 # More padding for thumbnails
        align = thumbnail_settings.get("정렬", "center")
        vertical_align = thumbnail_settings.get("수직정렬", "center")
        position = (self.resolution[0] // 2, self.resolution[1] // 2)

        # Generate 3 sets of images
        for i in range(min(3, len(thumbnail_texts) // 4)): # Ensure we have at least 4 lines per set
            current_texts = thumbnail_texts[i*4 : (i+1)*4]
            if not current_texts:
                continue

            # Print to terminal
            self._log(f"썸네일 텍스트 세트 {i+1}:")
            for line in current_texts:
                self._log(f"- {line}")

            image = Image.new("RGBA", self.resolution, (0, 0, 0, 0))
            
            # Join lines with newline characters for render_text_to_image
            full_text = "\n".join(current_texts)

            # Font size adjustment logic
            current_font_size = font_size
            temp_image = Image.new("RGBA", (1,1)) # Dummy image for text dimension calculation
            temp_draw = ImageDraw.Draw(temp_image)
            
            while True:
                temp_font = self.text_renderer._get_font(font_name, current_font_size)
                wrapped_lines = self.text_renderer._get_wrapped_text_lines(full_text, temp_font, max_width)
                
                total_text_height = 0
                for line in wrapped_lines:
                    _, h = self.text_renderer._get_text_dimensions(line, temp_font)
                    total_text_height += h * 1.2
                
                if total_text_height <= self.resolution[1] - 100 or current_font_size <= 20: # Stop if fits or too small
                    break
                current_font_size -= 2 # Reduce font size

            self._log(f"썸네일 텍스트 세트 {i+1} 최종 폰트 크기: {current_font_size}")

            self.text_renderer.render_text_to_image(
                image=image,
                text=full_text,
                position=position,
                font_name=font_name,
                font_size=current_font_size, # Use adjusted font size
                font_color=font_color,
                max_width=max_width,
                align=align,
                vertical_align=vertical_align
            )
            
            output_path = os.path.join(thumbnail_output_dir, f"{identifier}_thumbnail_{frame_counter:04d}.png")
            self.text_renderer.save_image(image, output_path)
            
            duration = self._estimate_speech_duration(full_text) # Estimate duration for thumbnail
            frame = SubtitleFrame(
                frame_number=frame_counter,
                start_time=0.0, # Thumbnails don't have specific timing in video
                end_time=0.0,
                duration=duration,
                scene_id=f"thumbnail_{i}",
                text=full_text,
                output_path=output_path
            )
            frames.append(frame)
            frame_counter += 1
            
        return frames

    def _estimate_speech_duration(self, text: str) -> float:
        return max(len(text) * 0.1, 1.0) # Simple estimation

    def _save_frame_info(self, script_type: str):
        frame_info = {
            "total_frames": len(self.frames),
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}",
            "output_directory": self.output_dir,
            "frames": [
                {
                    "frame_number": frame.frame_number,
                    "start_time": frame.start_time,
                    "end_time": frame.end_time,
                    "duration": frame.duration,
                    "scene_id": frame.scene_id,
                    "text": frame.text,
                    "output_path": frame.output_path
                }
                for frame in self.frames
            ]
        }
        
        file_suffix = {"회화": "conversation", "대화": "conversation", "인트로": "intro", "엔딩": "ending"}.get(script_type)
        output_path = os.path.join(self.output_dir, self.identifier, f"{self.identifier}_{file_suffix}_frames.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(frame_info, f, ensure_ascii=False, indent=2)
        
        self._log(f"✅ 프레임 정보 저장: {output_path}")
