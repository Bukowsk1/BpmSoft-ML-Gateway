FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY Backend/requirements.txt /app/Backend/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/Backend/requirements.txt

COPY Backend /app/Backend
COPY Karina /app/Karina
COPY Vlad /app/Vlad

WORKDIR /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "Backend", "--host", "0.0.0.0", "--port", "8000"]
