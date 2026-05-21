"""
CapCut 프로젝트 자동 생성기
draft_content.json + draft_meta_info.json + Resources 폴더를 생성해서
CapCut이 바로 열 수 있는 프로젝트를 만든다.

시간 단위: 마이크로초 (1초 = 1,000,000)
"""

import json
import uuid
import shutil
import os
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


# ── 상수 ──────────────────────────────────────────────────────────────────────
US = 1_000_000          # 1초 = 1,000,000 마이크로초
CAPCUT_PROJECTS = Path(r"C:\Users\user\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")


def uid() -> str:
    return str(uuid.uuid4()).upper()


def to_us(seconds: float) -> int:
    return int(seconds * US)


# ── 데이터 클래스 ─────────────────────────────────────────────────────────────
@dataclass
class ImageClip:
    path: str           # 이미지 파일 경로
    duration: float     # 표시 시간 (초)
    zoom: bool = True   # Ken Burns 줌 효과 여부
    zoom_in: bool = True  # True=줌인, False=줌아웃


@dataclass
class AudioClip:
    path: str           # 음성 파일 경로
    volume: float = 1.0


@dataclass
class Subtitle:
    text: str
    start: float        # 시작 시간 (초)
    duration: float     # 표시 시간 (초)
    font_size: int = 60
    color: str = "#FFFFFF"
    bold: bool = True


# ── 메인 빌더 ─────────────────────────────────────────────────────────────────
class CapCutBuilder:
    def __init__(
        self,
        name: str,
        width: int = 1920,
        height: int = 1080,
        fps: float = 30.0,
    ):
        self.name = name
        self.width = width
        self.height = height
        self.fps = fps

        # materials 저장소
        self._img_materials: list = []
        self._audio_materials: list = []
        self._text_materials: list = []

        # track segments
        self._video_segments: list = []
        self._audio_segments: list = []
        self._text_segments: list = []

        # 키프레임 (줌 효과용)
        self._kf_videos: list = []

        self._total_duration: int = 0  # 마이크로초

    # ── 이미지 클립 추가 ──────────────────────────────────────────────────────
    def add_images(self, clips: List[ImageClip], resource_dir: Path):
        cursor = 0
        for clip in clips:
            src = Path(clip.path)
            dest = resource_dir / src.name
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)

            mat_id = uid()
            seg_id = uid()
            dur_us = to_us(clip.duration)

            self._img_materials.append(self._image_material(mat_id, dest, dur_us))

            kf_refs = []
            if clip.zoom:
                kf_refs = self._make_zoom_keyframes(seg_id, dur_us, clip.zoom_in)

            self._video_segments.append(
                self._segment(seg_id, mat_id, cursor, dur_us, kf_refs)
            )
            cursor += dur_us

        self._total_duration = max(self._total_duration, cursor)

    # ── 오디오 추가 ───────────────────────────────────────────────────────────
    def add_audio(self, clip: AudioClip, resource_dir: Path):
        src = Path(clip.path)
        dest = resource_dir / src.name
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)

        mat_id = uid()
        seg_id = uid()

        # 오디오 전체 길이를 total_duration 에 맞춤
        dur_us = self._total_duration if self._total_duration > 0 else to_us(999)

        self._audio_materials.append(self._audio_material(mat_id, dest, dur_us, clip.volume))
        self._audio_segments.append(self._segment(seg_id, mat_id, 0, dur_us, []))

        self._total_duration = max(self._total_duration, dur_us)

    # ── 자막 추가 ─────────────────────────────────────────────────────────────
    def add_subtitles(self, subtitles: List[Subtitle]):
        for sub in subtitles:
            mat_id = uid()
            seg_id = uid()
            start_us = to_us(sub.start)
            dur_us = to_us(sub.duration)

            self._text_materials.append(self._text_material(mat_id, sub))
            self._text_segments.append(self._segment(seg_id, mat_id, start_us, dur_us, []))

    # ── 프로젝트 빌드 & 저장 ──────────────────────────────────────────────────
    def build(self, output_base: Path) -> Path:
        """
        output_base 아래에 self.name 폴더를 만들고
        CapCut 프로젝트 구조를 생성한다.
        CapCut 프로젝트 디렉토리(CAPCUT_PROJECTS)에도 심볼릭 링크 대신 직접 생성.
        """
        project_dir = output_base / self.name
        project_dir.mkdir(parents=True, exist_ok=True)
        resource_dir = project_dir / "Resources"
        resource_dir.mkdir(exist_ok=True)

        # 미디어 파일 복사 (add_images/add_audio 에서 이미 dest=resource_dir 로 복사함)
        # draft_content.json 생성
        content = self._build_content()
        (project_dir / "draft_content.json").write_text(
            json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # draft_meta_info.json 생성
        meta = self._build_meta(project_dir)
        (project_dir / "draft_meta_info.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # CapCut이 요구하는 빈 폴더들
        for d in ["adjust_mask", "common_attachment", "matting", "qr_upload",
                  "smart_crop", "subdraft", "draft_settings"]:
            (project_dir / d).mkdir(exist_ok=True)

        print(f"[CapCutBuilder] 프로젝트 생성 완료: {project_dir}")
        return project_dir

    def install_to_capcut(self, project_dir: Path):
        """
        생성된 프로젝트를 CapCut 프로젝트 폴더에 복사해서 바로 열 수 있게 한다.
        """
        dest = CAPCUT_PROJECTS / self.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(project_dir, dest)
        print(f"[CapCutBuilder] CapCut에 설치 완료: {dest}")
        return dest

    # ── draft_content.json 조립 ───────────────────────────────────────────────
    def _build_content(self) -> dict:
        now_us = int(time.time() * 1_000_000)

        tracks = []
        if self._video_segments:
            tracks.append({"id": uid(), "type": "video", "attribute": 0,
                           "flag": 0, "name": "", "is_default_name": True,
                           "segments": self._video_segments})
        if self._audio_segments:
            tracks.append({"id": uid(), "type": "audio", "attribute": 0,
                           "flag": 0, "name": "", "is_default_name": True,
                           "segments": self._audio_segments})
        if self._text_segments:
            tracks.append({"id": uid(), "type": "text", "attribute": 0,
                           "flag": 0, "name": "", "is_default_name": True,
                           "segments": self._text_segments})

        return {
            "id": uid(),
            "version": "6.9.0",
            "new_version": "119.0.0",
            "name": self.name,
            "duration": self._total_duration,
            "create_time": now_us,
            "update_time": now_us,
            "fps": self.fps,
            "is_drop_frame_timecode": False,
            "color_space": 0,
            "config": {
                "original_sound_volume": 1.0,
                "music_volume": 1.0,
            },
            "canvas_config": {
                "ratio": "original",
                "width": self.width,
                "height": self.height,
                "background": None,
            },
            "tracks": tracks,
            "group_container": None,
            "materials": self._build_materials(),
            "keyframes": {
                "videos": self._kf_videos,
                "audios": [], "texts": [], "stickers": [],
                "filters": [], "adjusts": [], "handwrites": [], "effects": [],
            },
            "keyframe_graph_list": [],
            "platform": {
                "app_id": 1775,
                "app_source": "lv",
                "app_version": "8.1.1",
                "device_id": "auto",
                "hard_disk_id": "",
                "mac_address": "",
                "os": "windows",
                "os_version": "11.0.0",
            },
            "last_modified_platform": {
                "app_id": 1775,
                "app_source": "lv",
                "app_version": "8.1.1",
                "device_id": "auto",
                "hard_disk_id": "",
                "mac_address": "",
                "os": "windows",
                "os_version": "11.0.0",
            },
            "mutable_config": None,
            "cover": "",
            "retouch_cover": "",
            "extra_info": None,
            "relationships": [],
            "render_index_track_mode_on": False,
            "free_render_index_mode_on": False,
            "static_cover_image_path": "",
            "source": "default",
            "time_marks": None,
            "path": "",
            "lyrics_effects": [],
            "uneven_animation_template_info": "",
            "draft_type": "",
            "smart_ads_info": "",
            "function_assistant_info": None,
        }

    def _build_materials(self) -> dict:
        empty = []
        return {
            "flowers": empty, "videos": empty,
            "tail_leaders": empty,
            "audios": self._audio_materials,
            "images": self._img_materials,
            "texts": self._text_materials,
            "effects": empty, "stickers": empty,
            "canvases": empty, "transitions": empty,
            "audio_effects": empty, "audio_fades": empty,
            "beats": empty,
            "material_animations": empty,
            "placeholders": empty, "placeholder_infos": empty,
            "speeds": empty, "common_mask": empty,
            "chromas": empty, "text_templates": empty,
            "realtime_denoises": empty, "audio_pannings": empty,
            "audio_pitch_shifts": empty, "video_trackings": empty,
            "hsl": empty, "drafts": empty, "color_curves": empty,
            "hsl_curves": empty, "primary_color_wheels": empty,
            "log_color_wheels": empty, "video_effects": empty,
            "audio_balances": empty, "handwrites": empty,
            "manual_deformations": empty, "manual_beautys": empty,
            "plugin_effects": empty, "sound_channel_mappings": empty,
            "green_screens": empty, "shapes": empty,
            "material_colors": empty, "digital_humans": empty,
            "digital_human_model_dressing": empty, "smart_crops": empty,
            "ai_translates": empty, "audio_track_indexes": empty,
            "loudnesses": empty, "vocal_beautifys": empty,
            "vocal_separations": empty, "smart_relights": empty,
            "time_marks": empty, "multi_language_refs": empty,
            "video_shadows": empty, "video_strokes": empty,
            "video_radius": empty,
        }

    def _build_meta(self, project_dir: Path) -> dict:
        now_us = int(time.time() * 1_000_000)
        return {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "cloud_package_completed_time": "",
            "draft_cloud_capcut_purchase_info": "",
            "draft_cloud_last_action_download": False,
            "draft_cloud_package_type": "",
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": "draft_cover.jpg",
            "draft_deeplink_url": "",
            "draft_enterprise_info": {
                "draft_enterprise_extra": "",
                "draft_enterprise_id": "",
                "draft_enterprise_name": "",
                "enterprise_material": [],
            },
            "draft_fold_path": str(project_dir).replace("\\", "/"),
            "draft_id": uid(),
            "draft_is_ae_produce": False,
            "draft_is_ai_packaging_used": False,
            "draft_is_ai_shorts": False,
            "draft_is_ai_translate": False,
            "draft_is_article_video_draft": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_from_deeplink": "false",
            "draft_is_invisible": False,
            "draft_is_web_article_video": False,
            "draft_materials": [
                {"type": 0, "value": []}, {"type": 1, "value": []},
                {"type": 2, "value": []}, {"type": 3, "value": []},
                {"type": 6, "value": []},
            ],
            "draft_materials_copied_info": [],
            "draft_name": self.name,
            "draft_need_rename_folder": False,
            "draft_new_version": "",
            "draft_removable_storage_device": "",
            "draft_root_path": str(CAPCUT_PROJECTS).replace("\\", "/"),
            "draft_segment_extra_info": [],
            "draft_timeline_materials_size_": 0,
            "draft_type": "",
            "draft_web_article_video_enter_from": "",
            "tm_draft_cloud_completed": "",
            "tm_draft_cloud_entry_id": -1,
            "tm_draft_cloud_modified": 0,
            "tm_draft_cloud_parent_entry_id": -1,
            "tm_draft_cloud_space_id": -1,
            "tm_draft_cloud_user_id": -1,
            "tm_draft_create": now_us,
            "tm_draft_modified": now_us,
            "tm_draft_removed": 0,
            "tm_duration": self._total_duration,
        }

    # ── 재료 팩토리 ───────────────────────────────────────────────────────────
    @staticmethod
    def _image_material(mat_id: str, path: Path, duration_us: int) -> dict:
        return {
            "id": mat_id,
            "type": "photo",
            "duration": duration_us,
            "path": str(path).replace("\\", "/"),
            "media_path": "",
            "local_id": "",
            "has_audio": False,
            "width": 1920,
            "height": 1080,
            "category_id": "",
            "category_name": "local",
            "material_id": "",
            "material_name": path.name,
            "material_url": "",
            "crop": {
                "upper_left_x": 0.0, "upper_left_y": 0.0,
                "upper_right_x": 1.0, "upper_right_y": 0.0,
                "lower_left_x": 0.0, "lower_left_y": 1.0,
                "lower_right_x": 1.0, "lower_right_y": 1.0,
            },
            "crop_ratio": "free",
            "crop_scale": 1.0,
            "extra_type_option": 0,
            "source": 0,
            "source_platform": 0,
            "formula_id": "",
            "check_flag": 62978047,
            "video_algorithm": {
                "algorithms": [], "time_range": None, "path": "",
                "gameplay_configs": [], "ai_in_painting_config": [],
                "complement_frame_config": None, "motion_blur_config": None,
                "deflicker": None, "noise_reduction": None,
                "quality_enhance": None, "super_resolution": None,
                "ai_background_configs": [], "smart_complement_frame": None,
                "aigc_generate": None, "aigc_generate_list": [],
                "mouth_shape_driver": None, "ai_expression_driven": None,
                "ai_motion_driven": None, "image_interpretation": None,
                "story_video_modify_video_config": {
                    "task_id": "", "is_overwrite_last_video": False,
                    "tracker_task_id": "",
                },
                "skip_algorithm_index": [],
            },
            "is_unified_beauty_mode": False,
            "object_locked": None,
            "smart_motion": None,
            "picture_from": "none",
            "picture_set_category_id": "",
            "picture_set_category_name": "",
            "team_id": "",
            "local_material_id": str(uuid.uuid4()),
            "origin_material_id": "",
            "request_id": "",
            "has_sound_separated": False,
            "is_text_edit_overdub": False,
            "is_ai_generate_content": False,
            "aigc_type": "none",
            "is_copyright": False,
            "aigc_history_id": "",
            "aigc_item_id": "",
            "live_photo_timestamp": -1,
            "live_photo_cover_path": "",
            "reverse_path": "",
            "intensifies_path": "",
            "cartoon": False,
            "matting": {
                "flag": 0, "path": "", "interactiveTime": [],
                "has_use_quick_brush": False, "strokes": [],
                "has_use_quick_eraser": False, "expansion": 0,
                "feather": 0, "reverse": False, "custom_matting_id": "",
                "enable_matting_stroke": False,
            },
            "audio_fade": None,
            "stable": {
                "stable_level": 0, "matrix_path": "",
                "time_range": {"start": 0, "duration": 0},
            },
        }

    @staticmethod
    def _audio_material(mat_id: str, path: Path, duration_us: int, volume: float) -> dict:
        return {
            "id": mat_id,
            "type": "extract_music",
            "name": path.stem,
            "duration": duration_us,
            "path": str(path).replace("\\", "/"),
            "category_name": "local",
            "wave_points": [],
            "music_id": "",
            "app_id": 0,
            "text_id": "",
            "tone_type": "",
            "source_platform": 0,
            "video_id": "",
            "effect_id": "",
            "resource_id": "",
            "third_resource_id": "",
            "category_id": "",
            "intensifies_path": "",
            "formula_id": "",
            "check_flag": 3,
            "team_id": "",
            "local_material_id": str(uuid.uuid4()),
            "tone_speaker": "",
            "mock_tone_speaker": "",
            "tone_effect_id": "",
            "tone_effect_name": "",
            "tone_platform": "",
            "cloned_model_type": "",
            "tone_category_id": "",
            "tone_category_name": "",
            "is_ugc": True,
            "is_ai_clone_tone": False,
            "is_ai_clone_tone_post": False,
            "lyric_type": 0,
            "tts_task_id": "",
            "tts_generate_scene": "",
            "ai_music_type": 0,
            "ai_music_enter_from": "",
            "ai_music_generate_scene": 0,
            "tts_benefit_info": {
                "benefit_type": "none", "benefit_log_id": "",
                "benefit_log_extra": "", "benefit_amount": -1,
            },
        }

    @staticmethod
    def _text_material(mat_id: str, sub: Subtitle) -> dict:
        return {
            "id": mat_id,
            "type": "text",
            "content": json.dumps({
                "styles": [{
                    "strVal": sub.text,
                    "type": "word",
                }],
                "words": {
                    "endTime": [],
                    "startTime": [],
                    "text": [],
                },
            }, ensure_ascii=False),
            "text_size": sub.font_size,
            "bold": sub.bold,
            "italic": False,
            "underline": False,
            "alignment": "center",
            "base_content": sub.text,
            "font_color": sub.color,
            "font_color_changed": False,
            "border_color": "#000000",
            "border_color_changed": False,
            "border_width": 0.08,
            "use_effect_default_color": True,
            "background_color": "",
            "background_alpha": 1.0,
            "background_height": 0.14,
            "background_width": 0.14,
            "background_round_radius": 0.0,
            "background_style": 0,
            "font_category_id": "",
            "font_category_name": "",
            "font_id": "",
            "font_name": "",
            "font_path": "",
            "font_resource_id": "",
            "font_size": float(sub.font_size),
            "font_source_platform": 0,
            "font_team_id": "",
            "font_title": "NotoSansSC-Regular",
            "font_url": "",
            "global_alpha": 1.0,
            "has_shadow": False,
            "initial_scale": 1.0,
            "inner_padding": -1.0,
            "is_text_edit_overdub": False,
            "letter_spacing": 0.0,
            "line_feed": 1,
            "line_max_width": 0.82,
            "line_spacing": 0.02,
            "preset_id": "",
            "recognition_id": "",
            "recognition_path": "",
            "shape_clip_X": False,
            "shape_clip_Y": False,
            "source_from": "",
            "style_name": "",
            "sub_type": "",
            "subtitle_keywords": None,
            "template_id": "",
            "template_name": "",
            "template_scene": "default",
            "text_curve": None,
            "text_preset_resource_id": "",
            "text_to_audio_ids": [],
            "tts_auto_update": False,
            "type": "subtitle",
            "typesetting": 0,
            "unclear_text_color": "",
            "unclear_text_preset_id": "",
            "unclear_text_style_name": "",
            "words": {
                "end_time": [],
                "start_time": [],
                "text": [],
            },
        }

    # ── 세그먼트 팩토리 ───────────────────────────────────────────────────────
    @staticmethod
    def _segment(
        seg_id: str,
        mat_id: str,
        start_us: int,
        dur_us: int,
        kf_refs: list,
    ) -> dict:
        return {
            "id": seg_id,
            "material_id": mat_id,
            "source_timerange": {"start": 0, "duration": dur_us},
            "target_timerange": {"start": start_us, "duration": dur_us},
            "render_timerange": {"start": 0, "duration": 0},
            "desc": "",
            "state": 0,
            "speed": 1.0,
            "is_loop": False,
            "is_tone_modify": False,
            "reverse": False,
            "intensifies_audio": False,
            "cartoon": False,
            "volume": 1.0,
            "last_nonzero_volume": 1.0,
            "clip": {
                "scale": {"x": 1.0, "y": 1.0},
                "rotation": 0.0,
                "transform": {"x": 0.0, "y": 0.0},
                "flip": {"vertical": False, "horizontal": False},
                "alpha": 1.0,
            },
            "uniform_scale": {"on": True, "value": 1.0},
            "extra_material_refs": [],
            "render_index": 0,
            "keyframe_refs": [],
            "common_keyframes": kf_refs,
            "enable_lut": True,
            "enable_adjust": True,
            "enable_hsl": False,
            "visible": True,
            "group_id": "",
            "enable_color_curves": True,
            "enable_hsl_curves": True,
            "track_render_index": 0,
            "hdr_settings": {"mode": 1, "intensity": 1.0, "nits": 1000},
            "enable_color_wheels": True,
            "track_attribute": 0,
            "is_placeholder": False,
            "template_id": "",
            "enable_smart_color_adjust": False,
            "template_scene": "default",
            "caption_info": None,
            "responsive_layout": {
                "enable": False, "target_follow": "",
                "size_layout": 0, "horizontal_pos_layout": 0,
                "vertical_pos_layout": 0,
            },
            "enable_color_match_adjust": False,
            "enable_color_correct_adjust": False,
            "enable_adjust_mask": False,
            "raw_segment_id": "",
            "lyric_keyframes": None,
            "enable_video_mask": True,
            "digital_human_template_group_id": "",
            "color_correct_alg_result": "",
            "source": "segmentsourcenormal",
            "enable_mask_stroke": False,
            "enable_mask_shadow": False,
        }

    # ── Ken Burns 줌 키프레임 ─────────────────────────────────────────────────
    def _make_zoom_keyframes(
        self, seg_id: str, dur_us: int, zoom_in: bool
    ) -> list:
        """
        이미지에 줌인 또는 줌아웃 효과를 주는 키프레임을 생성한다.
        scale 1.0 → 1.15 (줌인) 또는 1.15 → 1.0 (줌아웃)
        """
        kf_id = uid()
        start_scale = 1.0 if zoom_in else 1.15
        end_scale = 1.15 if zoom_in else 1.0

        keyframe_entry = {
            "id": kf_id,
            "property_type": "KFTypeUniformScale",
            "keyframe_list": [
                {
                    "id": uid(),
                    "time_offset": 0,
                    "values": [start_scale],
                    "left_control": {"x": 0.0, "y": 0.0},
                    "right_control": {"x": 0.0, "y": 0.0},
                    "curveType": "Line",
                },
                {
                    "id": uid(),
                    "time_offset": dur_us,
                    "values": [end_scale],
                    "left_control": {"x": 0.0, "y": 0.0},
                    "right_control": {"x": 0.0, "y": 0.0},
                    "curveType": "Line",
                },
            ],
        }
        self._kf_videos.append(keyframe_entry)
        return [{"id": uid(), "keyframe_id": kf_id, "material_id": seg_id}]
