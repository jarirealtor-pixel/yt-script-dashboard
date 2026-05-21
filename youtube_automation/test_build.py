"""
실제 파일 없이도 동작 테스트 - 더미 이미지와 빈 오디오로 프로젝트 생성 확인
"""
import struct
import wave
from pathlib import Path
from PIL import Image
from capcut_builder import CapCutBuilder, ImageClip, AudioClip, Subtitle


def make_test_image(path: Path, color: tuple, text: str = ""):
    """테스트용 이미지 생성"""
    img = Image.new("RGB", (1920, 1080), color)
    img.save(path)
    print(f"  이미지 생성: {path.name}")


def make_test_audio(path: Path, duration_sec: float = 30.0):
    """테스트용 무음 WAV 생성"""
    sample_rate = 44100
    num_samples = int(sample_rate * duration_sec)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(b"\x00\x00" * num_samples)
    print(f"  오디오 생성: {path.name} ({duration_sec}초)")


def run_test():
    print("=" * 60)
    print("CapCut 자동화 테스트 시작")
    print("=" * 60)

    # 테스트 에셋 폴더
    asset_dir = Path("test_assets")
    asset_dir.mkdir(exist_ok=True)
    output_dir = Path("output")
    resource_dir = output_dir / "부동산테스트" / "Resources"
    resource_dir.mkdir(parents=True, exist_ok=True)

    print("\n[1] 테스트 에셋 생성...")
    colors = [
        ((41, 128, 185), "서울 아파트 동향"),
        ((39, 174, 96), "강남 매매가 분석"),
        ((142, 68, 173), "전세 vs 월세"),
        ((231, 76, 60), "금리 영향 분석"),
        ((243, 156, 18), "투자 전략 2026"),
    ]

    image_paths = []
    for i, (color, label) in enumerate(colors):
        img_path = asset_dir / f"scene_{i+1:02d}.jpg"
        make_test_image(img_path, color, label)
        image_paths.append(str(img_path))

    audio_path = asset_dir / "voice.wav"
    make_test_audio(audio_path, duration_sec=30.0)

    print("\n[2] 자막 데이터 준비...")
    subtitles = [
        Subtitle("2026년 서울 부동산 시장 완전 분석", start=0.0, duration=4.0),
        Subtitle("강남 아파트 매매가 5% 상승", start=4.5, duration=4.0),
        Subtitle("전세 수요가 월세로 이동 중", start=9.5, duration=4.0),
        Subtitle("기준금리 동결이 부동산에 미치는 영향", start=14.5, duration=5.0),
        Subtitle("지금 투자해야 할 지역 TOP 3", start=20.0, duration=4.5),
    ]
    print(f"  자막 {len(subtitles)}개 준비 완료")

    print("\n[3] CapCut 프로젝트 빌드...")
    clips = [
        ImageClip(path=image_paths[i], duration=6.0, zoom=True, zoom_in=(i % 2 == 0))
        for i in range(len(image_paths))
    ]

    builder = CapCutBuilder(name="부동산테스트")
    builder.add_images(clips, resource_dir)
    builder.add_audio(AudioClip(path=str(audio_path)), resource_dir)
    builder.add_subtitles(subtitles)

    project_dir = builder.build(output_dir)

    print("\n[4] 결과 확인...")
    import json
    content = json.loads((project_dir / "draft_content.json").read_text(encoding="utf-8"))
    print(f"  전체 영상 길이: {content['duration'] / 1_000_000:.1f}초")
    print(f"  트랙 수: {len(content['tracks'])}")
    for t in content["tracks"]:
        print(f"    - {t['type']} 트랙: 세그먼트 {len(t['segments'])}개")
    print(f"  이미지 재료: {len(content['materials']['images'])}개")
    print(f"  오디오 재료: {len(content['materials']['audios'])}개")
    print(f"  텍스트 재료: {len(content['materials']['texts'])}개")
    print(f"  키프레임(줌): {len(content['keyframes']['videos'])}개")

    print("\n[5] CapCut에 설치...")
    try:
        builder.install_to_capcut(project_dir)
        print("  CapCut 설치 완료! CapCut을 열면 '부동산테스트' 프로젝트가 보입니다.")
    except Exception as e:
        print(f"  설치 실패: {e}")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print(f"프로젝트 경로: {project_dir.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
