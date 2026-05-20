FROM python:3.14-alpine

WORKDIR /app

# build tools needed for packages that compile C extensions (e.g. pydantic-core)
RUN apk add --no-cache gcc musl-dev libffi-dev

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copying all code into container
COPY appinfo ./appinfo/
COPY observability ./observability/
COPY app.py .

# immediate stdout/stderr output + preventing .pyc file creation
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# creating a non-root user to run the application
RUN adduser -D -s /bin/sh app && chown -R app:app /app
USER app

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8110"]
