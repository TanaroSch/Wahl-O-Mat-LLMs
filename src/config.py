import os

# Global configuration for the project
PROVIDER = "ollama"
MODEL_ID = "phi4:14b"
BASE_DATA_DIR = "../data"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")