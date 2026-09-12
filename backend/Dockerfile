FROM python:3.12.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY fluxyz ./fluxyz
RUN pip install --no-cache-dir .
RUN useradd --create-home fluxyz
USER fluxyz
CMD ["sh", "-c", "uvicorn fluxyz.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
