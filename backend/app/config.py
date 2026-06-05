"""
Application configuration loaded from environment variables / .env file.

All settings are validated at startup via pydantic-settings.
If a required variable is missing, the app will refuse to start
with a clear error message rather than failing silently at runtime.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Spotify OAuth ---
    spotify_client_id: str
    spotify_client_secret: str
    # Must match exactly what you registered in the Spotify Developer Dashboard
    redirect_uri: str = "http://127.0.0.1:8000/api/auth/callback"

    # --- Session ---
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    session_secret: str

    # --- URLs ---
    frontend_url: str = "http://localhost:5173"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Single shared instance — import this everywhere
settings = Settings()
