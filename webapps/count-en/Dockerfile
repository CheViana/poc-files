FROM library/python:3.10-slim

COPY count-en.py /app/count-en.py
COPY requirements.txt /app/requirements.txt
COPY dict.txt /app/dict.txt
COPY gcp-creds.json /app/gcp-creds.json

WORKDIR /app

ENV PYTHONUNBUFFERED=1
RUN pip install -r /app/requirements.txt

EXPOSE 8083

CMD ["python", "/app/brokenphone.py"]
