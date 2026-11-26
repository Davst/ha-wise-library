FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium \
    && groupadd --gid 10001 library \
    && useradd --uid 10001 --gid library --create-home library
COPY app /app/app
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
