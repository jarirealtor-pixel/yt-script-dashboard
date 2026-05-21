"""
ElevenLabs TTS 모듈
- 대본 텍스트 → MP3 음성 파일 생성
- 자막 타이밍(SRT) 동시 생성
"""

import os
import json
import requests
from pathlib import Path
from capcut_builder import Subtitle


ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"


class ElevenLabsTTS:
    def __init__(self, api_key: str, voice_id: str = ""):
        self.api_key = api_key
        # 기본 보이스: Rachel (영어) / 한국어는 voice_id 직접 지정 필요
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"
        self.headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }

    def list_voices(self) -> list[dict]:
        """사용 가능한 보이스 목록 조회"""
        resp = requests.get(f"{ELEVENLABS_API_URL}/voices", headers=self.headers)
        resp.raise_for_status()
        return resp.json()["voices"]

    def text_to_speech(
        self,
        text: str,
        output_path: str,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
    ) -> str:
        """
        텍스트 → MP3 파일 생성
        Returns: 저장된 파일 경로
        """
        url = f"{ELEVENLABS_API_URL}/text-to-speech/{self.voice_id}"
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": True,
            },
        }

        print(f"[TTS] 음성 생성 중... ({len(text)}자)")
        resp = requests.post(url, headers=self.headers, json=payload)
        resp.raise_for_status()

        Path(output_path).write_bytes(resp.content)
        print(f"[TTS] 저장 완료: {output_path}")
        return output_path

    def text_to_speech_with_timestamps(
        self,
        text: str,
        output_audio_path: str,
        model_id: str = "eleven_multilingual_v2",
    ) -> tuple[str, list[Subtitle]]:
        """
        텍스트 → MP3 + 자막 타이밍 동시 생성
        Returns: (audio_path, subtitles)
        """
        url = f"{ELEVENLABS_API_URL}/text-to-speech/{self.voice_id}/with-timestamps"
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        print(f"[TTS] 타임스탬프 포함 음성 생성 중... ({len(text)}자)")
        resp = requests.post(url, headers=self.headers, json=payload)
        resp.raise_for_status()

        data = resp.json()

        # 오디오 저장 (base64 디코딩)
        import base64
        audio_bytes = base64.b64decode(data["audio_base64"])
        Path(output_audio_path).write_bytes(audio_bytes)
        print(f"[TTS] 오디오 저장: {output_audio_path}")

        # 자막 타이밍 파싱
        subtitles = self._parse_timestamps(data.get("alignment", {}))
        print(f"[TTS] 자막 {len(subtitles)}개 생성")

        return output_audio_path, subtitles

    def _parse_timestamps(self, alignment: dict, chunk_size: int = 30) -> list[Subtitle]:
        """
        ElevenLabs alignment 데이터 → Subtitle 리스트
        chunk_size: 자막 한 줄 최대 글자 수
        """
        chars = alignment.get("characters", [])
        starts = alignment.get("character_start_times_seconds", [])
        ends = alignment.get("character_end_times_seconds", [])

        if not chars or not starts:
            return []

        # 글자들을 청크로 묶어서 자막 생성
        subtitles = []
        buf = ""
        buf_start = 0.0
        buf_end = 0.0

        for ch, s, e in zip(chars, starts, ends):
            if not buf:
                buf_start = s
            buf += ch
            buf_end = e

            # 공백/구두점에서 또는 chunk_size 초과 시 자막 분리
            if (ch in " .,!?。、！？" or len(buf) >= chunk_size) and buf.strip():
                text = buf.strip()
                if text:
                    subtitles.append(Subtitle(
                        text=text,
                        start=buf_start,
                        duration=buf_end - buf_start,
                    ))
                buf = ""

        if buf.strip():
            subtitles.append(Subtitle(
                text=buf.strip(),
                start=buf_start,
                duration=buf_end - buf_start,
            ))

        return subtitles


def generate_tts(
    script: str,
    output_dir: str,
    api_key: str = "",
    voice_id: str = "",
) -> tuple[str, list[Subtitle]]:
    """
    대본 → 오디오 + 자막 반환
    api_key가 없으면 환경변수 ELEVENLABS_API_KEY 사용
    """
    key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
    if not key:
        raise ValueError(
            "ElevenLabs API 키 필요: ELEVENLABS_API_KEY 환경변수 설정 또는 api_key 인자 전달"
        )

    out = Path(output_dir)
    out.mkdir(exist_ok=True)
    audio_path = str(out / "voice.mp3")

    tts = ElevenLabsTTS(api_key=key, voice_id=voice_id)
    return tts.text_to_speech_with_timestamps(script, audio_path)


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    test_script = """
    2026년 서울 부동산 시장 완전 분석입니다.
    강남 아파트 매매가가 5퍼센트 상승했으며
    전세 수요가 월세로 빠르게 이동하고 있습니다.
    지금 투자해야 할 지역 TOP 3를 알아보겠습니다.
    """

    key = os.getenv("ELEVENLABS_API_KEY", "")
    if not key:
        print("ELEVENLABS_API_KEY 환경변수를 설정해주세요.")
        print("예: set ELEVENLABS_API_KEY=your_key_here")
        sys.exit(1)

    audio, subs = generate_tts(test_script, "test_assets", api_key=key)
    print(f"\n오디오: {audio}")
    print("자막 샘플:")
    for s in subs[:5]:
        print(f"  [{s.start:.2f}s ~ {s.start+s.duration:.2f}s] {s.text}")
