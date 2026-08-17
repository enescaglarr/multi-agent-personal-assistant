"""
Configuration settings for Personal Assistant API.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the Personal Assistant API."""

    # Groq Configuration (OpenAI-compatible endpoint)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "1"))

    # TAVILY
    TAVILY_SEARCH_KEY: str = os.getenv("TAVILY_SEARCH_KEY", "")
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "5"))

    # Google API Configuration
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_TOKEN_FILE: str = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    GOOGLE_SCOPES: list = [
        'https://www.googleapis.com/auth/calendar',
        'https://mail.google.com/']

    # Timezone Configuration
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")

    # Weather API Configuration
    OPEN_METEO_URL: str = "https://api.open-meteo.com/v1/forecast"
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/search"


# Initialize and validate configuration
config = Config()
