import os

# Global configuration for the project
PROVIDER = "ollama"
MODEL_ID = "phi3.5:latest"
DEBUG_STREAM = True # currently only used for Ollama
BASE_DATA_DIR = "../data"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")