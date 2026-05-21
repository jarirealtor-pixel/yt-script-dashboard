"""
유튜브 자동화 - 메인 실행 스크립트
사용법:
  python main.py --images img1.jpg img2.jpg --audio voice.mp3 --srt subs.srt --name 내영상

SRT 없이 자막을 직접 지정하려면 코드에서 subtitles 리스트를 수정하면 된다.
"""

import argparse
import re
from pathlib import Path
from capcut_builder import CapCutBuilder, ImageClip, AudioClip, Subtitle


# ── SRT 파서 ──────────────────────────────────────────────────────────────────
def parse_srt(srt_path: str) -> list[Subtitle]:
    text = Path(srt_path).read_text(encoding="utf-8")
    blocks = re.split(r"\n\n+", text.strip())
    subs = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        # 타이밍 파싱: 00:00:01,000 --> 00:00:04,500
        m = re.match(
            r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)",
            lines[1],
        )
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
        content = " ".join(lines[2:]).strip()
        subs.append(Subtitle(text=content, start=start, duration=end - start))
    return subs


# ── 이미지 타이밍 자동 분배 ────────────────────────────────────────────────────
def distribute_images(image_paths: list[str], total_duration: float) -> list[ImageClip]:
    """오디오 길이에 맞게 이미지를 균등 배분"""
    n = len(image_paths)
    dur = total_duration / n
    clips = []
    for i, p in enumerate(image_paths):
        clips.append(ImageClip(
            path=p,
            duration=dur,
            zoom=True,
            zoom_in=(i % 2 == 0),  # 짝수=줌인, 홀수=줌아웃으로 교대
        ))
    return clips


# ── 오디오 길이 읽기 ──────────────────────────────────────────────────────────
def get_audio_duration(audio_path: str) -> float:
    """mutagen 또는 ffprobe로 오디오 길이 읽기"""
    try:
        from mutagen import File
        f = File(audio_path)
        if f is not None and f.info:
            return f.info.length
    except ImportError:
        pass
    # fallback: ffprobe
    import subprocess, json as _json
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", audio_path],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        data = _json.loads(result.stdout)
        return float(data["format"]["duration"])
    # 최후 수단: 60초로 가정
    print(f"[경고] 오디오 길이 읽기 실패, 60초로 가정: {audio_path}")
    return 60.0


# ── 메인 ──────────────────────────────────────────────────────────────────────
def build_project(
    name: str,
    image_paths: list[str],
    audio_path: str,
    subtitles: list[Subtitle],
    output_dir: str = "output",
    install: bool = True,
) -> Path:
    output_base = Path(output_dir)
    output_base.mkdir(exist_ok=True)
    resource_dir = output_base / name / "Resources"
    resource_dir.mkdir(parents=True, exist_ok=True)

    # 오디오 길이 기준으로 이미지 타이밍 계산
    audio_dur = get_audio_duration(audio_path)
    print(f"[main] 오디오 길이: {audio_dur:.1f}초")
    print(f"[main] 이미지: {len(image_paths)}장")
    print(f"[main] 자막: {len(subtitles)}개")

    clips = distribute_images(image_paths, audio_dur)

    builder = CapCutBuilder(name=name)
    builder.add_images(clips, resource_dir)
    builder.add_audio(AudioClip(path=audio_path), resource_dir)
    if subtitles:
        builder.add_subtitles(subtitles)

    project_dir = builder.build(output_base)

    if install:
        builder.install_to_capcut(project_dir)

    return project_dir


def main():
    parser = argparse.ArgumentParser(description="CapCut 프로젝트 자동 생성")
    parser.add_argument("--name", required=True, help="프로젝트 이름")
    parser.add_argument("--images", nargs="+", required=True, help="이미지 파일 경로들")
    parser.add_argument("--audio", required=True, help="음성 파일 경로 (mp3/wav)")
    parser.add_argument("--srt", default=None, help="자막 SRT 파일 경로 (선택)")
    parser.add_argument("--output", default="output", help="출력 폴더")
    parser.add_argument("--no-install", action="store_true", help="CapCut에 자동 설치 안 함")
    args = parser.parse_args()

    subtitles = parse_srt(args.srt) if args.srt else []

    build_project(
        name=args.name,
        image_paths=args.images,
        audio_path=args.audio,
        subtitles=subtitles,
        output_dir=args.output,
        install=not args.no_install,
    )
    print("[완료] CapCut을 열면 프로젝트가 보입니다. Export만 누르세요!")


if __name__ == "__main__":
    main()
