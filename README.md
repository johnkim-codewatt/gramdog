# Grammar Dog
* public 배포용 프로젝트

Dog처럼 꽉 물고 “문법 놓치지 않을 거야~”를 목표로 한 AI 영어 학습 프로젝트입니다. 웹 클라이언트, API 백엔드, 안드로이드 앱으로 구성되어 있습니다.

---

## doc

**역할:** Grammar Dog의 기획·아키텍처·기능 개선·파인튜닝·모바일(엣지) 실험을 글로 남긴 자료 모음입니다. 마크다운 본문과 함께 UI·흐름도용 **스크린샷 이미지**(PNG)가 포함되어 있어, 저장소만으로도 설계 의도와 작업 맥락을 따라가기 쉽습니다.

**주요 문서** (`doc/`)

| 파일 | 내용 요약 |
| --- | --- |
| `01.AI_영어학습기_Grammar_Dog.md` | 프로젝트 취지, 학습·구현 접근, 초기 구현 계획·사용자 흐름·기술 스택 방향 |
| `02.AI_영어학습기_파인튜닝.md` | 파인튜닝·데이터 엔지니어링, LLM 기반 데이터 증류, 정·부정 샘플 비율 등 학습 데이터 전략 |
| `03.AI_영어학습기_기능개선.md` | LangGraph 기반 단계 제어, Self-RAG·의도 분류, 인덱싱·문법 가이드(atlas) 활용 등 배포 전 기능·품질 개선 |
| `04.AI_영어학습기_파인튜닝_모바일작업.md` | 안드로이드 연동, 온디바이스 경량 모델·TFLite 이식, API 비용·지연·프라이버시 관점의 역할 분담 |

---

## client

**역할:** Next.js 기반 웹 UI. 학습 화면·인터랙션을 제공합니다.

**사용 기술**

- [Next.js](https://nextjs.org/) 16, [React](https://react.dev/) 19
- [TypeScript](https://www.typescriptlang.org/)
- [Tailwind CSS](https://tailwindcss.com/) 4, PostCSS, Autoprefixer
- [Lottie](https://airbnb.io/lottie/#/web) (`lottie-web`)
- [ESLint](https://eslint.org/) (`eslint-config-next`)

로컬 개발은 `client` 디렉터리에서 `npm install` 후 `npm run dev`를 사용합니다.

---

## backend

**역할:** FastAPI REST API, LangGraph 기반 튜터 파이프라인(문제 생성·피드백·이력 RAG 등), PostgreSQL(pgvector)과 연동한 학습 이력·문법 데이터 처리. CLI 스크립트(`app.py` 등)로 로컬 대화형 테스트도 가능합니다.

**사용 기술**

- [Python](https://www.python.org/) 3.11 (Dockerfile 기준)
- [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
- [LangGraph](https://langchain-ai.github.io/langgraph/), [LangChain](https://www.langchain.com/) (`langchain-openai`, `langchain-core`)
- [OpenAI API](https://platform.openai.com/docs) (채팅·임베딩)
- [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) (`docker-compose`의 `pgvector/pgvector` 이미지)
- [psycopg2](https://www.psycopg.org/), [Pydantic](https://docs.pydantic.dev/), [PyYAML](https://pyyaml.org/), [python-dotenv](https://github.com/theskumar/python-dotenv)
- [Docker](https://www.docker.com/) / Compose (DB 및 배포용 이미지 구성)

HTTP API 엔트리포인트는 `backend/api.py`의 FastAPI `app` 객체입니다. (로컬 실행 시 `uvicorn api:app --reload` 등)

DB는 `backend/docker-compose.yml`을 참고하면 됩니다. 설계·작업 기록은 위 **doc** 섹션을 참고하세요.

---

## mobile

**역할:** Android 네이티브 앱. Jetpack Compose UI와 TensorFlow Lite로 온디바이스 추론(의도 분류 등)을 시험·연동하고, `BuildConfig`로 백엔드 베이스 URL 등을 주입해 API와 연결할 수 있습니다.

**사용 기술**

- [Kotlin](https://kotlinlang.org/), [Jetpack Compose](https://developer.android.com/jetpack/compose), Material 3
- [Android Gradle Plugin](https://developer.android.com/build) 8.x, Kotlin 2.2
- [TensorFlow Lite](https://www.tensorflow.org/lite)
- 모델 변환·실험 스크립트: `mobile/export_tflite.py` 등 — [PyTorch](https://pytorch.org/), [Hugging Face Transformers](https://huggingface.co/docs/transformers), [LiteRT / litert-torch](https://ai.google.dev/edge/litert) (변환 파이프라인에 사용)

앱 모듈 경로: `mobile/AITestApp/`. 에뮬레이터 기본 백엔드 주소는 `10.0.2.2`로 맞춰 둔 설정이 있습니다(`BACKEND_BASE_URL` Gradle 프로퍼티로 변경 가능).
