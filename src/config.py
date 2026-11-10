"""
Configuration module for the NIRF Conversational Analytical Assistant.
Provides centralized path management, environment settings, and canonical constants.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project Root Directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data Paths
# Supports both data/NIRF_Final_Cleaned_Dataset and NIRF_Final_Cleaned_Dataset
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "NIRF_Final_Cleaned_Dataset"
FALLBACK_DATA_DIR = PROJECT_ROOT / "NIRF_Final_Cleaned_Dataset"

if DEFAULT_DATA_DIR.exists():
    DATA_DIR = DEFAULT_DATA_DIR
elif FALLBACK_DATA_DIR.exists():
    DATA_DIR = FALLBACK_DATA_DIR
else:
    DATA_DIR = DEFAULT_DATA_DIR

# Canonical Data File Paths
MASTER_DATASET_PATH = DATA_DIR / "nirf_master_cleaned.csv"
COMPARABILITY_RULES_PATH = DATA_DIR / "comparability_rules.csv"
DATA_DICTIONARY_PATH = DATA_DIR / "data_dictionary.xlsx"
INSTITUTION_MAPPING_PATH = DATA_DIR / "institution_mapping.csv"
FINAL_VALIDATION_REPORT_PATH = DATA_DIR / "final_validation_report.md"
COMPARABILITY_REPORT_PATH = DATA_DIR / "comparability_report.md"

# Knowledge Base & Vector Store Paths
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"
KB_NIRF_DIR = KNOWLEDGE_BASE_DIR / "nirf"
KB_PROJECT_DIR = KNOWLEDGE_BASE_DIR / "project"
VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"
DATABASE_DIR = PROJECT_ROOT / "database"
CONVERSATION_DB_PATH = DATABASE_DIR / "conversations.db"

# RAG Configuration
RAG_DATA_DIR = PROJECT_ROOT / "data" / "rag"
RAG_INDEX_DIR = RAG_DATA_DIR / "index"
APPROVED_DOCUMENTS_PATH = RAG_DATA_DIR / "approved_documents.json"
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSION = 384
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120
DEFAULT_RETRIEVAL_TOP_K = 5

# LLM Configuration
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))
OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))

# Standard Dataset Dimensions & Bounds
VALID_YEARS = list(range(2017, 2026))

STANDARD_PARAMETERS = ["tlr", "rpc", "go", "oi", "perception"]
RESEARCH_PARAMETERS = ["research_sfc", "research_qnr", "research_qlr", "oi", "perception"]
CORE_METRICS = ["score", "rank"] + STANDARD_PARAMETERS + ["research_sfc", "research_qnr", "research_qlr"]

PRIMARY_KEY_COLUMNS = ["year", "category", "institution_uid"]

# Expected Column Count
EXPECTED_COLUMN_COUNT = 40

