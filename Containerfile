FROM python:3.13.5-bookworm

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copying all code into container
COPY . .

# immediate stdout/stderr output + preventing .pyc file creation
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# creating a non-root user to run the application
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8110", "--reload"]
