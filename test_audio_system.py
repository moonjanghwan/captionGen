import json
import os
import shutil
import unittest
from unittest.mock import MagicMock, patch

from src.pipeline.audio.generator import AudioGenerator
from src.pipeline.audio.ssml_builder import SSMLBuilder

def _mock_synthesize_speech_side_effect(ssml_text, output_path, voice_name, language_code):
    # Simulate creating a dummy audio file
    with open(output_path, "wb") as f:
        f.write(b"dummy_audio_content")
    return 1.0, [] # Return a dummy duration and empty marks

def _mock_subprocess_run_side_effect(command, check, capture_output, text):
    # Simulate ffmpeg creating the output file
    # The output path for ffmpeg concat is usually the second to last argument
    output_path = command[-2]
    with open(output_path, "wb") as f:
        f.write(b"dummy_merged_audio_content")
    return MagicMock(returncode=0, stdout="", stderr="")

class TestAudioSystem(unittest.TestCase):

    def setUp(self):
        self.test_output_dir = "test_output_audio_system"
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        self.config = {
            "output_directory": self.test_output_dir,
            "tts": {
                "native_voice": "ko-KR-Standard-A",
                "learner_1_voice": "en-US-Standard-C",
                "learner_2_voice": "en-US-Standard-D",
                "learner_3_voice": "en-US-Standard-E",
                "learner_4_voice": "en-US-Standard-F",
                "native_lang_code": "ko-KR",
                "learning_lang_code": "en-US"
            }
        }
        
        self.ssml_builder = SSMLBuilder(
            native_speaker_name=self.config["tts"]["native_voice"],
            native_lang_code=self.config["tts"]["native_lang_code"],
            learner_speaker_names=[
                self.config["tts"]["learner_1_voice"],
                self.config["tts"]["learner_2_voice"],
                self.config["tts"]["learner_3_voice"],
                self.config["tts"]["learner_4_voice"],
            ],
            learning_lang_code=self.config["tts"]["learning_lang_code"]
        )

    def tearDown(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def test_ssml_builder_conversation_parts(self):
        print("\n--- Testing SSMLBuilder Conversation Parts ---")
        sequence = 1
        native_script = "안녕하세요! 반갑습니다."
        learning_script = "Hello! Nice to meet you."
        learner_speaker_name = self.config["tts"]["learner_1_voice"]

        native_ssml = self.ssml_builder.build_conversation_ssml_native_part(sequence, native_script)
        self.assertIn(native_script, native_ssml)
        self.assertIn(f'<mark name="scene_{sequence}_native_start"/>', native_ssml)
        self.assertIn(f'<voice name="{self.config["tts"]["native_voice"]}" xml:lang="{self.config["tts"]["native_lang_code"]}">', native_ssml)
        print("✅ Native SSML part generated correctly.")

        learner_ssml = self.ssml_builder.build_conversation_ssml_learner_part(sequence, learning_script, learner_speaker_name)
        self.assertIn(learning_script, learner_ssml)
        self.assertIn(f'<mark name="scene_{sequence}_learner_{learner_speaker_name}_start"/>', learner_ssml)
        self.assertIn(f'<voice name="{learner_speaker_name}" xml:lang="{self.config["tts"]["learning_lang_code"]}">', learner_ssml)
        print("✅ Learner SSML part generated correctly.")

    def test_ssml_builder_intro_ending(self):
        print("\n--- Testing SSMLBuilder Intro/Ending ---")
        scene_id = "intro_001"
        text = "환영합니다!"

        intro_ssml = self.ssml_builder.build_intro_ending_ssml(scene_id, text)
        self.assertIn(text, intro_ssml)
        self.assertIn(f'<mark name="{scene_id}_start"/>', intro_ssml)
        self.assertIn(f'<voice name="{self.config["tts"]["native_voice"]}" xml:lang="{self.config["tts"]["native_lang_code"]}">', intro_ssml)
        print("✅ Intro/Ending SSML generated correctly.")

    @patch('src.pipeline.audio.generator.texttospeech.TextToSpeechClient')
    @patch('src.pipeline.audio.generator.subprocess.run', side_effect=_mock_subprocess_run_side_effect)
    @patch('src.pipeline.audio.generator.AudioGenerator._synthesize_speech', side_effect=_mock_synthesize_speech_side_effect)
    @patch('src.pipeline.audio.generator.AudioGenerator._get_accurate_audio_duration', return_value=1.5) # Mock duration
    def test_audio_generator_conversation(self, mock_get_accurate_audio_duration, mock_synthesize_speech, mock_subprocess_run, mock_tts_client):
        print("\n--- Testing AudioGenerator Conversation ---")
        # mock_instance = mock_tts_client.return_value
        # mock_instance.synthesize_speech.return_value = MagicMock(audio_content=b"dummy_audio", time_pings=[])
        # mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="1.23\n", stderr="")

        generator = AudioGenerator(self.config)
        
        manifest_data = {
            "identifier": "test_conv",
            "project_name": "test_project",
            "scenes": [
                {
                    "native_script": "안녕하세요",
                    "learning_script": "Hello"
                },
                {
                    "native_script": "잘 지내셨어요?",
                    "learning_script": "How have you been?"
                }
            ]
        }

        # Explicitly create parent directories for the test
        base_output_path = os.path.join(self.test_output_dir, manifest_data["project_name"], manifest_data["identifier"])
        os.makedirs(os.path.join(base_output_path, "mp3"), exist_ok=True)
        os.makedirs(os.path.join(base_output_path, "SSML"), exist_ok=True)

        result = generator.generate_conversation_audio(manifest_data)
        
        self.assertTrue(result["success"])
        self.assertIn("test_conv_conversation.mp3", result["audio_file"])
        self.assertIn("test_conv_conversation.ssml", result["ssml_file"])
        self.assertTrue(os.path.exists(result["audio_file"]))
        self.assertTrue(os.path.exists(result["ssml_file"]))
        print("✅ Conversation audio generation successful.")

    @patch('src.pipeline.audio.generator.texttospeech.TextToSpeechClient')
    @patch('src.pipeline.audio.generator.subprocess.run', side_effect=_mock_subprocess_run_side_effect)
    @patch('src.pipeline.audio.generator.AudioGenerator._synthesize_speech', side_effect=_mock_synthesize_speech_side_effect)
    @patch('src.pipeline.audio.generator.AudioGenerator._get_accurate_audio_duration', return_value=1.0) # Mock duration
    def test_audio_generator_intro_ending(self, mock_get_accurate_audio_duration, mock_synthesize_speech, mock_subprocess_run, mock_tts_client):
        print("\n--- Testing AudioGenerator Intro/Ending ---")
        # mock_instance = mock_tts_client.return_value
        # mock_instance.synthesize_speech.return_value = MagicMock(audio_content=b"dummy_audio", time_pings=[])
        # mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="0.87\n", stderr="")

        generator = AudioGenerator(self.config)
        
        manifest_data = {
            "identifier": "test_intro",
            "project_name": "test_project",
            "scenes": [
                {
                    "id": "intro_scene_1",
                    "text": "첫 번째 인트로 문장입니다."
                },
                {
                    "id": "intro_scene_2",
                    "text": "두 번째 인트로 문장입니다."
                }
            ]
        }

        # Explicitly create parent directories for the test
        base_output_path = os.path.join(self.test_output_dir, manifest_data["project_name"], manifest_data["identifier"])
        os.makedirs(os.path.join(base_output_path, "mp3"), exist_ok=True)
        os.makedirs(os.path.join(base_output_path, "SSML"), exist_ok=True)

        result = generator.generate_intro_ending_audio(manifest_data, "intro")
        
        self.assertTrue(result["success"])
        self.assertIn("test_intro_intro.mp3", result["audio_file"])
        self.assertIn("test_intro_intro.ssml", result["ssml_file"])
        self.assertTrue(os.path.exists(result["audio_file"]))
        self.assertTrue(os.path.exists(result["ssml_file"]))
        print("✅ Intro audio generation successful.")

        manifest_data["identifier"] = "test_ending"
        result = generator.generate_intro_ending_audio(manifest_data, "ending")
        
        self.assertTrue(result["success"])
        self.assertIn("test_ending_ending.mp3", result["audio_file"])
        self.assertIn("test_ending_ending.ssml", result["ssml_file"])
        self.assertTrue(os.path.exists(result["audio_file"]))
        self.assertTrue(os.path.exists(result["ssml_file"]))
        print("✅ Ending audio generation successful.")

if __name__ == '__main__':
    unittest.main()