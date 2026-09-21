FROM python:3.14-alpine@sha256:016508ba505da24f7139765bc4bb669df4e88eb2f12eeadd571bf2f88d7533df

LABEL maintainer="me@nyorf.com"
LABEL org.opencontainers.image.title="tbank-webhooks"

WORKDIR /app

# build tools for packages that compile c extensions; git for the vcs dependency
RUN apk add --no-cache gcc musl-dev libffi-dev git

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY appinfo ./appinfo/
COPY app.py .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# uid and gid fixed at 10001 and stated numerically in USER, so the identity holds wherever the image runs and needs
# no lookup in /etc/passwd; the pod spec asks for the same uid and gid
RUN addgroup -g 10001 app && adduser -D -u 10001 -G app -s /bin/sh app && chown -R 10001:10001 /app
USER 10001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8110"]
