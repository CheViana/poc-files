FROM library/python:3.10-slim

COPY brokenphone.py /app/brokenphone.py
COPY requirements.txt /app/requirements.txt

WORKDIR /app

ENV PYTHONUNBUFFERED=1
RUN pip install -r /app/requirements.txt

CMD ["python", "/app/brokenphone.py"]
