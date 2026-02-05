"""
Settings: Load configuration from environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class Settings:
    """Application settings loaded from environment."""
    
    # LLM Configuration
    llm_provider: str = "openai"  # openai, anthropic, google
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Model settings
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 2000
    
    # Data settings
    data_path: str = "data/sample_events.csv"
    schema_path: str = "data/schema.json"
    knowledge_path: str = "data/knowledge.json"
    
    # Logging
    log_level: str = "INFO"
    
    # Project root for resolving paths
    project_root: Path = PROJECT_ROOT
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            model_name=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            temperature=float(os.getenv("TEMPERATURE", "0.0")),
            max_tokens=int(os.getenv("MAX_TOKENS", "2000")),
            data_path=os.getenv("DATA_PATH", "data/sample_events.csv"),
            schema_path=os.getenv("SCHEMA_PATH", "data/schema.json"),
            knowledge_path=os.getenv("KNOWLEDGE_PATH", "data/knowledge.json"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            project_root=PROJECT_ROOT,
        )
    
    def get_api_key(self) -> Optional[str]:
        """Get the API key for the configured provider."""
        if self.llm_provider == "openai":
            return self.openai_api_key
        elif self.llm_provider == "anthropic":
            return self.anthropic_api_key
        elif self.llm_provider == "google":
            return self.google_api_key
        return None
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert a relative path to absolute path from project root."""
        return self.project_root / relative_path
    
    def validate(self) -> tuple[bool, str]:
        """Validate that required settings are present."""
        api_key = self.get_api_key()
        if not api_key:
            return False, f"No API key found for provider: {self.llm_provider}"
        
        data_file = self.get_absolute_path(self.data_path)
        if not data_file.exists():
            return False, f"Data file not found: {data_file}"
        
        schema_file = self.get_absolute_path(self.schema_path)
        if not schema_file.exists():
            return False, f"Schema file not found: {schema_file}"
        
        return True, "Settings are valid"


# Global settings instance
settings = Settings.from_env()


if __name__ == "__main__":
    print(f"Provider: {settings.llm_provider}")
    print(f"Model: {settings.model_name}")
    print(f"Data path: {settings.get_absolute_path(settings.data_path)}")
    
    valid, msg = settings.validate()
    print(f"Valid: {valid} - {msg}")
