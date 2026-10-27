FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY bot.py releases.py ./
RUN useradd -m bot && chown -R bot /app
USER bot
CMD ["python", "bot.py"]
