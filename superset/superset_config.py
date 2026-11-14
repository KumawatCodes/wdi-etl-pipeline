"""Runtime configuration for the self-hosted Superset instance."""

import os

from sqlalchemy.engine import URL


SQLALCHEMY_DATABASE_URI = URL.create(
    "postgresql+psycopg2",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["DB_PASSWORD"],
    host="postgres",
    port=5432,
    database="superset_metadata",
).render_as_string(hide_password=False)

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

WTF_CSRF_ENABLED = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
TALISMAN_ENABLED = False  # The browser connection is protected by an SSH tunnel.
