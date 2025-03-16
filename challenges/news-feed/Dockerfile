FROM python:3.13-alpine

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

RUN python3 -m flask --app app init-db

EXPOSE 5000
CMD ["python3", "-m" , "flask", "run", "--host=0.0.0.0"]