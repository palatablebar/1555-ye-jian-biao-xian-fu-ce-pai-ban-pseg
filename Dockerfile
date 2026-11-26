FROM python:3.12-slim
WORKDIR /workspace
ENV PYTHONPATH=/workspace/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "-m", "linebeads.entry", "serve"]
