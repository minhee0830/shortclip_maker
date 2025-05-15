# Python 베이스 이미지
FROM python:3.11-slim

# 시스템 패키지 설치 (ffmpeg 포함)
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# 앱 작업 디렉토리 설정
WORKDIR /app

# requirements 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 소스 복사
COPY . .

# 포트 설정
ENV PORT=5000

# 실행 명령
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
