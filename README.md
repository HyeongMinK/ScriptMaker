# ScriptMaker

> **LLM + RAG 기반 발표 스크립트 자동 생성 및 립싱크 영상 제작 시스템**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)](https://openai.com)
[![Wav2Lip](https://img.shields.io/badge/Wav2Lip-Lip--sync-blue)](https://github.com/Rudrabha/Wav2Lip)

---

## 개요

ScriptMaker는 프레젠테이션 준비 과정에서 발생하는 **스크립트 작성 부담**을 획기적으로 줄이기 위해 설계된 웹 애플리케이션입니다.

기존 자동화 서비스들은 PPT를 단순 요약하는 수준에 머물러 발표자의 개별 의도나 맥락을 충분히 반영하지 못했습니다. ScriptMaker는 **사용자의 구어체 음성 발화**를 핵심 입력으로 삼아, 발표자가 강조하고 싶은 내용을 그대로 살린 스크립트를 생성합니다. 나아가 생성된 스크립트를 **TTS + 립싱크 영상**으로까지 이어지는 파이프라인을 단일 인터페이스 안에서 제공합니다.

---

## 주요 기능

### 1. PDF 업로드 및 슬라이드 뷰어
- PPT를 PDF로 변환하여 업로드
- 슬라이드별 이미지·텍스트 자동 추출 (PyMuPDF)
- 사이드바에서 페이지 간 자유로운 이동

### 2. 음성 녹음 → 스크립트 생성
- 슬라이드별 마이크 녹음
- **Whisper**로 STT 변환 (한국어 특화)
- **GPT-4o + RAG**로 발표체 스크립트 자동 생성
  - 사용자 발화를 최우선으로 반영
  - PPT 텍스트와 보조 자료를 결합
  - 이전 페이지 맥락을 참조해 발표 흐름 유지
  - 환각 방지를 위한 엄격한 Source-based Prompting

### 3. 보조 자료 업로드 (RAG)
- TXT, DOC, DOCX, PDF, PPTX 지원
- OpenAI Vector Store에 임베딩
- 스크립트 생성 시 관련 내용만 선택적으로 인용

### 4. 스타일 옵션
| 옵션 | 설명 |
|------|------|
| **Default** | 일반적인 발표 문체 |
| **Politely and Academically** | 격식체·학술 어투 |
| **Using RAG** | 보조 자료 활용 ON/OFF |

### 5. 다국어 번역
- 완성된 전체 스크립트를 원하는 언어로 일괄 번역
- 지원 언어: English, 中文, 日本語, Tiếng Việt, हिन्दी
- GPT-4o-mini로 원문 어조 유지하며 번역

### 6. TTS + 립싱크 영상 생성
- **OpenAI TTS**로 스크립트를 음성 합성
- 사이드바 카메라로 촬영한 사진 + 음성 → **Wav2Lip** 립싱크
- 원문 스크립트 / 번역 스크립트 각각 영상 제작 가능
- 완성된 영상 다운로드 후 PPT에 삽입 가능

---

## 시스템 아키텍처

```
PDF 업로드
    │
    ▼
슬라이드 파싱 (PyMuPDF)
    │
    ├─ 텍스트 추출 ──────────────────────────────┐
    │                                           │
    ▼                                           │
마이크 녹음                                     │
    │                                           │
    ▼                                           ▼
Whisper STT ──────────►  스크립트 생성
                              │
                    ┌─────────┴──────────┐
                    │  RAG (Vector Store) │  ← 보조 자료
                    └─────────┬──────────┘
                              ▼
                        발표 스크립트
                              │
                    ┌─────────┴──────────┐
                    │                    │
                    ▼                    ▼
              OpenAI TTS          다국어 번역
                    │
                    ▼
              Wav2Lip 립싱크
                    │
                    ▼
              영상 다운로드
```

---

## 설치 및 실행

### 1. 환경 설정

```bash
git clone <repo-url>
cd 25-1_v2
pip install -r requirements.txt
```

> **주의:** PyTorch, OpenCV, librosa는 별도 설치가 필요합니다.
> ```bash
> pip install torch torchvision opencv-python librosa
> ```

ffmpeg은 시스템 패키지로 설치합니다.

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt-get install ffmpeg
```

### 2. 환경 변수

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. 실행

```bash
streamlit run app.py
```

---

## 사용 방법

1. **PDF 업로드** — PPT를 PDF로 변환 후 업로드
2. **슬라이드 선택** — 사이드바에서 작업할 페이지 선택
3. **음성 녹음** — 해당 슬라이드에 대해 자유롭게 말하기
4. **스크립트 확인 및 수정** — AI 생성 스크립트를 직접 편집 가능
5. **영상 생성 페이지 이동** — "Go to Video Creation" 클릭
6. **(선택) 전체 번역** — 원하는 언어로 일괄 번역
7. **영상 생성** — 사진 촬영 후 각 슬라이드의 영상 생성 및 다운로드

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| **프론트엔드** | Streamlit |
| **음성 인식** | OpenAI Whisper |
| **스크립트 생성** | GPT-4o + OpenAI Assistants API |
| **번역** | GPT-4o-mini |
| **RAG** | OpenAI Vector Store (File Search) |
| **TTS** | OpenAI TTS (echo voice) |
| **립싱크** | Wav2Lip |
| **PDF 처리** | PyMuPDF (fitz) |
| **오디오** | pydub, librosa |
| **영상** | OpenCV, FFmpeg |

---

## 성능 비교

뤼튼(Wrtn) 대비 비교 실험에서 ScriptMaker는 다음 측면에서 우수한 결과를 보였습니다.

| 평가 항목 | 뤼튼 | ScriptMaker |
|-----------|------|-------------|
| 사용자 의도 반영도 | 낮음 (PPT 요약 중심) | 높음 (발화 기반) |
| 정보 충실도 | 낮음 (할루시네이션 발생) | 높음 (출처 기반 생성) |
| PPT 텍스트 없는 슬라이드 | 처리 어려움 | 발화 + RAG로 보완 |
| 다국어 지원 | 제한적 | 5개 언어 번역 |
| 립싱크 영상 생성 | 미지원 | 지원 |

---

## 한계 및 향후 연구

- **처리 시간**: 슬라이드마다 녹음이 필요해 전체 스크립트 즉시 생성 대비 시간이 소요됨
- **단일 LLM**: 현재 GPT-4o만 지원, 다른 모델과의 비교 미수행
- **향후 계획**: 커스텀 TTS (사용자 목소리 클로닝), 다국어 STT 확장, 사용자 만족도 정량 평가

---

## 프로젝트 정보

**Digital Wellness Lab**
Maintained by HyeongMin Kim · 2025
