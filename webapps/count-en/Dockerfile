FROM library/python:3.10-slim

COPY dict.txt /app/dict.txt
COPY count-en.py /app/count-en.py
COPY requirements.txt /app/requirements.txt
COPY charged-scholar-399420-ab7ede7e134a.json /app/charged-scholar-399420-ab7ede7e134a.json

WORKDIR /app

ENV PYTHONUNBUFFERED=1
RUN pip install -r /app/requirements.txt

EXPOSE 8083

CMD ["python", "/app/count-en.py"]
