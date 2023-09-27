FROM library/python:3.10-slim

COPY echo.py /app/echo.py

WORKDIR /app

RUN pip install aiohttp

ENV PYTHONUNBUFFERED=1

EXPOSE 8083

CMD ["python", "/app/echo.py"]
