"""
Configuration settings for the consultant matching system.
"""

import os
from typing import Optional
# For Pydantic v2 compatibility
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5433/consultant_matching"
    
    # Redis (optional)
    redis_url: Optional[str] = "redis://localhost:6380"
    
    # Embeddings
    embedding_backend: str = "local"  # "openai" or "local"
    openai_api_key: Optional[str] = None
    
    # Scraping Settings
    scraping_enabled: bool = True
    scraping_rate_limit: float = 1.0  # Seconds between requests
    scraping_max_pages: int = 10  # Max pages per source
    scraping_timeout: int = 30  # Request timeout in seconds
    
    # Scraping Schedules (cron format)
    brainville_schedule: str = "0 7 * * *"  # Daily at 07:00
    cinode_schedule: str = "0 7 * * *"
    linkedin_schedule: str = "0 8 * * *"  # Staggered to avoid load
    ework_schedule: str = "0 8 * * *"
    
    # Notification Settings
    slack_webhook_url: Optional[str] = None
    teams_webhook_url: Optional[str] = None
    notification_enabled: bool = True
    
    # Matching Thresholds
    perfect_match_threshold: float = 0.95
    high_quality_threshold: float = 0.80
    min_match_threshold: float = 0.60
    max_matches_per_job: int = 10
    
    # Report Settings
    daily_report_time: str = "07:30"  # Time to send daily reports
    weekly_report_day: str = "friday"  # Day to send weekly reports
    weekly_report_time: str = "16:00"
    monday_summary_time: str = "08:00"  # Monday morning summary
    
    # n8n Integration
    n8n_webhook_url: Optional[str] = None
    n8n_enabled: bool = False
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    api_debug: bool = False
    
    # Security
    api_key: Optional[str] = None  # Optional API key for endpoints
    jwt_secret: Optional[str] = None  # For future JWT implementation
    secret_key: Optional[str] = None  # JWT secret key
    cors_origins: list = ["*"]  # Allowed CORS origins
    
    # External Services
    context7_api_key: Optional[str] = None
    playwright_enabled: bool = False
    playwright_proxy: Optional[str] = None
    cinode_username: Optional[str] = None
    cinode_password: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Feature Flags
    auto_matching_enabled: bool = True
    auto_embedding_enabled: bool = True
    duplicate_detection_enabled: bool = True
    
    # Data Retention
    job_retention_days: int = 90  # How long to keep job postings
    match_retention_days: int = 180  # How long to keep match results
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Scraper-specific configurations
SCRAPER_CONFIGS = {
    "brainville": {
        "enabled": True,
        "base_url": "https://www.brainville.com",
        "max_pages": settings.scraping_max_pages,
        "rate_limit": settings.scraping_rate_limit,
    },
    "cinode": {
        "enabled": True,
        "base_url": "https://www.cinode.com",
        "api_endpoint": "/api/marketplace/assignments",  # If API is available
        "max_pages": settings.scraping_max_pages,
        "rate_limit": settings.scraping_rate_limit,
    },
    "linkedin": {
        "enabled": True,
        "base_url": "https://www.linkedin.com",
        "search_params": {
            "keywords": "consultant",
            "location": "Sweden",
            "job_type": "contract",
        },
        "max_pages": 5,  # LinkedIn is more restrictive
        "rate_limit": 2.0,  # Slower rate for LinkedIn
    },
    "ework": {
        "enabled": True,  # Now implemented!
        "base_url": "https://app.verama.com",
        "countries": ["SE"],  # Configure target countries
        "languages": ["SV", "EN"],  # Swedish and English
        "max_pages": settings.scraping_max_pages,
        "rate_limit": settings.scraping_rate_limit,
    },
    "onsiter": {
        "enabled": False,
        "base_url": "https://www.onsiter.com",
        "max_pages": settings.scraping_max_pages,
        "rate_limit": settings.scraping_rate_limit,
    },
}


# Swedish-specific configurations
SWEDISH_COMPANIES = [
    # Major consulting companies
    "Capgemini", "Accenture", "CGI", "TietoEVRY", "HiQ",
    "Knowit", "Sigma", "Netlight", "McKinsey", "BCG",
    
    # Tech companies
    "Ericsson", "Volvo", "Scania", "SAAB", "ABB",
    "Spotify", "Klarna", "King", "Mojang", "Paradox",
    
    # Banks and Finance
    "SEB", "Swedbank", "Nordea", "Handelsbanken", "Skandia",
    
    # Telecom
    "Telia", "Tele2", "Telenor", "3 Sverige",
    
    # Retail
    "H&M", "IKEA", "ICA", "Coop", "Axfood",
]


SWEDISH_CITIES = [
    "Stockholm", "Göteborg", "Malmö", "Uppsala", "Västerås",
    "Örebro", "Linköping", "Helsingborg", "Jönköping", "Norrköping",
    "Lund", "Umeå", "Gävle", "Borås", "Södertälje", "Eskilstuna",
    "Karlstad", "Täby", "Växjö", "Halmstad", "Sundsvall",
    "Trollhättan", "Östersund", "Borlänge", "Falun", "Kalmar",
    "Skövde", "Karlskrona", "Kristianstad", "Skellefteå",
]


# Skill aliases for better matching
SKILL_ALIASES = {
    "JavaScript": ["JS", "Javascript", "javascript"],
    "TypeScript": ["TS", "typescript"],
    "C#": ["CSharp", "C-Sharp", "csharp"],
    ".NET": ["DotNet", "dotnet", "asp.net", "ASP.NET"],
    "Node.js": ["NodeJS", "Node", "nodejs"],
    "React": ["ReactJS", "React.js"],
    "Vue": ["VueJS", "Vue.js"],
    "Angular": ["AngularJS", "Angular.js"],
    "PostgreSQL": ["Postgres", "PgSQL"],
    "MySQL": ["Maria", "MariaDB"],
    "Kubernetes": ["K8s", "k8s"],
    "CI/CD": ["CI", "CD", "CICD"],
}