"""
유튜브 자동화 오케스트레이터
Claude API를 사용해서 대본 생성부터 CapCut 프로젝트 생성까지 자동화한다.

워크플로우:
  1. [기획] Claude → 주제 분석 + 대본 생성
  2. [TTS]  ElevenLabs → 음성 + 자막 타이밍
  3. [이미지] DALL-E / 로컬 이미지 → 씬별 이미지
  4. [편집] CapCutBuilder → 프로젝트 폴더 생성 + CapCut 설치
  5. [업로드] YouTube API → 업로드 (선택)

사용:
  python orchestrator.py --topic "강남 아파트 2026 전망" --images img1.jpg img2.jpg
  python orchestrator.py --topic "전세 사기 예방법" --auto-images  # DALL-E로 이미지 자동 생성
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime

import anthropic

from capcut_builder import CapCutBuilder, ImageClip, AudioClip, Subtitle
from tts import generate_tts
from main import build_project


# ── Claude 기반 대본 생성 ──────────────────────────────────────────────────────
class ScriptWriter:
    def __init__(self, api_key: str = ""):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", "")
        )
        self.model = "claude-sonnet-4-6"

    def generate_script(
        self,
        topic: str,
        target_duration: int = 300,  # 초
        style: str = "정보성",
        reference_titles: list[str] = None,
    ) -> dict:
        """
        주제 → 유튜브 대본 생성
        Returns: {title, hook, script, scenes, tags, thumbnail_text}
        """
        ref_section = ""
        if reference_titles:
            ref_section = f"\n참고 영상 제목들:\n" + "\n".join(f"- {t}" for t in reference_titles)

        prompt = f"""당신은 부동산/재테크 유튜브 채널의 전문 PD입니다.
아래 주제로 {target_duration//60}분짜리 {style} 유튜브 영상 대본을 작성해주세요.
{ref_section}

주제: {topic}

다음 JSON 형식으로 반환해주세요:
{{
  "title": "클릭율 높은 영상 제목 (30자 이내)",
  "thumbnail_text": "썸네일에 들어갈 짧은 문구 (10자 이내)",
  "hook": "첫 10초 후킹 문장 (시청자가 계속 보게 만드는 강렬한 문장)",
  "script": "전체 대본 (나레이션만, 약 {target_duration * 4}자)",
  "scenes": [
    {{"seq": 1, "duration": 6, "description": "씬 설명", "image_prompt": "영어로 된 이미지 생성 프롬프트"}},
    ...
  ],
  "tags": ["태그1", "태그2", ...],
  "description": "유튜브 영상 설명 (500자 이내)"
}}

대본 작성 원칙:
- 인트로: 후킹 질문으로 시작 (시청자가 끝까지 볼 이유 제시)
- 본론: 구체적 수치와 사례 포함
- 아웃트로: 구독/좋아요 유도
- 씬은 6~8초 단위로 구성 (총 {target_duration // 7}개 내외)
- 이미지 프롬프트는 "realistic photo, Korean apartment building, ..." 형식"""

        print(f"[Claude] 대본 생성 중: '{topic}'")
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = resp.content[0].text
        # JSON 블록 추출
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        result = json.loads(raw)
        print(f"[Claude] 대본 생성 완료: '{result['title']}'")
        return result

    def choose_strategy(self, scripts: list[dict]) -> dict:
        """
        여러 대본 후보 중 최적안 선택 (오토 모드)
        """
        if len(scripts) == 1:
            return scripts[0]

        options = "\n\n".join(
            f"[옵션 {i+1}]\n제목: {s['title']}\n후킹: {s['hook']}"
            for i, s in enumerate(scripts)
        )

        prompt = f"""다음 유튜브 영상 후보들 중 조회수가 가장 높을 것을 선택하고,
선택 이유를 간단히 설명해주세요.
JSON으로 반환: {{"selected": 1, "reason": "이유"}}

{options}"""

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text
        if "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        data = json.loads(raw)
        idx = data["selected"] - 1
        print(f"[Claude] 전략 선택: 옵션 {data['selected']} - {data['reason']}")
        return scripts[idx]


# ── 이미지 생성 (DALL-E) ──────────────────────────────────────────────────────
def generate_images_dalle(
    scenes: list[dict],
    output_dir: Path,
    api_key: str = "",
) -> list[str]:
    """씬별 이미지 프롬프트 → DALL-E 이미지 생성"""
    import requests as req

    key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("OPENAI_API_KEY 환경변수 설정 필요")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    image_paths = []

    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", f"Korean real estate, modern apartment, professional photo")
        print(f"[DALL-E] 이미지 {i+1}/{len(scenes)} 생성: {prompt[:50]}...")

        resp = req.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json={
                "model": "dall-e-3",
                "prompt": f"Photorealistic, high quality. {prompt}. No text, no watermark.",
                "n": 1,
                "size": "1792x1024",
                "quality": "standard",
            },
        )
        resp.raise_for_status()
        img_url = resp.json()["data"][0]["url"]

        img_resp = req.get(img_url)
        img_path = output_dir / f"scene_{i+1:02d}.jpg"
        img_path.write_bytes(img_resp.content)
        image_paths.append(str(img_path))
        print(f"[DALL-E] 저장: {img_path.name}")

    return image_paths


# ── 메인 오케스트레이터 ───────────────────────────────────────────────────────
def run(
    topic: str,
    project_name: str = "",
    image_paths: list[str] = None,
    auto_images: bool = False,
    target_duration: int = 300,
    elevenlabs_key: str = "",
    elevenlabs_voice_id: str = "",
    openai_key: str = "",
    upload_to_youtube: bool = False,
    youtube_privacy: str = "private",
):
    name = project_name or datetime.now().strftime("%Y%m%d_%H%M")
    work_dir = Path("output") / name
    work_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = work_dir / "assets"
    asset_dir.mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"주제: {topic}")
    print(f"프로젝트: {name}")
    print(f"{'='*60}\n")

    # ── Step 1: 대본 생성 ────────────────────────────────────────────────────
    writer = ScriptWriter()
    script_data = writer.generate_script(topic, target_duration=target_duration)

    # 대본 저장
    (work_dir / "script.json").write_text(
        json.dumps(script_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[1/5] 대본 저장: {work_dir / 'script.json'}")

    # ── Step 2: TTS ─────────────────────────────────────────────────────────
    elabs_key = elevenlabs_key or os.getenv("ELEVENLABS_API_KEY", "")
    if elabs_key:
        audio_path, subtitles = generate_tts(
            script=script_data["script"],
            output_dir=str(asset_dir),
            api_key=elabs_key,
            voice_id=elevenlabs_voice_id,
        )
        print(f"[2/5] TTS 완료: {audio_path}, 자막 {len(subtitles)}개")
    else:
        print("[2/5] ELEVENLABS_API_KEY 없음 → TTS 건너뜀 (수동으로 voice.mp3 준비 필요)")
        audio_path = str(asset_dir / "voice.mp3")
        subtitles = []

    # ── Step 3: 이미지 준비 ──────────────────────────────────────────────────
    if auto_images:
        oai_key = openai_key or os.getenv("OPENAI_API_KEY", "")
        images = generate_images_dalle(script_data["scenes"], asset_dir, api_key=oai_key)
        print(f"[3/5] DALL-E 이미지 {len(images)}장 생성 완료")
    elif image_paths:
        images = image_paths
        print(f"[3/5] 수동 이미지 {len(images)}장 사용")
    else:
        print("[3/5] 이미지 없음 → test_assets의 기본 이미지 사용")
        images = sorted(str(p) for p in Path("test_assets").glob("*.jpg"))

    # ── Step 4: CapCut 프로젝트 생성 ─────────────────────────────────────────
    if Path(audio_path).exists():
        project_dir = build_project(
            name=name,
            image_paths=images,
            audio_path=audio_path,
            subtitles=subtitles,
            output_dir=str(Path("output")),
            install=True,
        )
        print(f"[4/5] CapCut 프로젝트 설치 완료")
    else:
        print(f"[4/5] 오디오 파일 없음 ({audio_path}) → CapCut 생성 건너뜀")
        project_dir = None

    # ── Step 5: YouTube 업로드 (선택) ─────────────────────────────────────────
    if upload_to_youtube and project_dir:
        exported_video = project_dir / f"{name}.mp4"
        if exported_video.exists():
            from youtube_upload import upload_video, save_upload_info
            vid = upload_video(
                video_path=str(exported_video),
                title=script_data["title"],
                description=script_data["description"],
                tags=script_data.get("tags", []),
                privacy=youtube_privacy,
            )
            save_upload_info(vid, script_data, str(work_dir))
            print(f"[5/5] YouTube 업로드 완료: https://youtube.com/watch?v={vid}")
        else:
            print(f"[5/5] {exported_video} 없음 → CapCut에서 Export 후 재실행하세요")

    print(f"\n{'='*60}")
    print("완료 요약:")
    print(f"  제목: {script_data['title']}")
    print(f"  후킹: {script_data['hook'][:60]}...")
    if project_dir:
        print(f"  CapCut: '부동산' 프로젝트 열고 Export 버튼 누르세요")
    print(f"{'='*60}\n")

    return script_data


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="유튜브 자동화 오케스트레이터")
    parser.add_argument("--topic", required=True, help="영상 주제")
    parser.add_argument("--name", default="", help="프로젝트 이름 (없으면 날짜시간)")
    parser.add_argument("--images", nargs="*", default=None, help="이미지 파일 경로들")
    parser.add_argument("--auto-images", action="store_true", help="DALL-E로 이미지 자동 생성")
    parser.add_argument("--duration", type=int, default=300, help="목표 영상 길이 (초)")
    parser.add_argument("--upload", action="store_true", help="YouTube 자동 업로드")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = parser.parse_args()

    run(
        topic=args.topic,
        project_name=args.name,
        image_paths=args.images,
        auto_images=args.auto_images,
        target_duration=args.duration,
        upload_to_youtube=args.upload,
        youtube_privacy=args.privacy,
    )
