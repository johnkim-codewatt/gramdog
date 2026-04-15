# 1. 가볍고 빠른 Python 공식 이미지 사용 (콜드 스타트 방어)
FROM python:3.11-slim

# 2. 파이썬 환경 변수 설정 (버퍼링 방지 및 바이트코드 생성 방지)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 의존성 파일 먼저 복사 및 설치 (도커 캐시 활용으로 빌드 속도 UP)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 5. 나머지 소스코드 전체 복사
COPY . /app/

# 6. Cloud Run이 주입해주는 PORT 환경 변수 수신 대기 (기본값 8080)
ENV PORT 8080

# 7. 서버 실행 (FastAPI 기준)
# 주의: main.py 안에 app 객체가 있어야 함
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]