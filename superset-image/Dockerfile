FROM apache/superset:6.0.0

USER root
RUN . /app/.venv/bin/activate \
    && uv pip install --no-cache psycopg2-binary==2.9.12

USER superset
