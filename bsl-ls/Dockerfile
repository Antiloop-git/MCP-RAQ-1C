FROM eclipse-temurin:17-jre-alpine

RUN apk add --no-cache python3 py3-pip curl \
    && pip3 install --break-system-packages flask==3.1.* --no-cache-dir

WORKDIR /app

# Download BSL Language Server
ARG BSL_LS_VERSION=0.28.5
RUN curl -fsSL -o bsl-ls.jar \
    "https://github.com/1c-syntax/bsl-language-server/releases/download/v${BSL_LS_VERSION}/bsl-language-server-${BSL_LS_VERSION}-exec.jar"

COPY server.py .

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["python3", "server.py"]
