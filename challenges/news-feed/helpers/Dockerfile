FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

RUN python3 -m playwright install --with-deps chromium-headless-shell

COPY admin_simulator.py app.py

CMD ["python3", "app.py"]