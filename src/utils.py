import json
import logging
import os
from typing import Dict, Any, List

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Loads configuration, providing sensible defaults for a global CLI tool.
    Optionally reads overrides from a local .fgen.json or variables.json.
    """
    defaults = {
        "GENAI_MODEL": "gemini-2.5-pro",
        "ANKICONNECT_URL": "http://127.0.0.1:8765",
        "ANKI_DECK_NAME": "Default Deck",
        "ANKI_MODEL_NAME": "Stochastic Processes Model",
        "ANKI_OUTPUT_PATH": "deck.apkg",
        "FLASHCARD_FILE_PATH": "flashcards.json",
        "PROCESSED_FILES_PATH": "processed_files.json"
    }

    # If config_path is not explicitly provided, try to find a local config
    if not config_path:
        if os.path.exists('.fgen.json'):
            config_path = '.fgen.json'
        elif os.path.exists('variables.json'):
            config_path = 'variables.json'

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                defaults.update(user_config)
                logging.info(f"Loaded configuration from {config_path}")
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {config_path}. Using defaults.")

    return defaults

def get_processed_files(path: str) -> List[str]:
    """
    Retrieves the list of processed files from a JSON file.
    
    Parameters
    ----------
    - path: str
        The path to the processed files JSON.

    Returns
    -------
    - List[str]
        A list of processed file paths.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def add_processed_file(path: str, file_path: str):
    """
    Adds a file path to the list of processed files.

    Parameters
    ----------
    - path: str
        The path to the processed files JSON.
    - file_path: str
        The path of the file to add.
    """
    processed_files = get_processed_files(path)
    if file_path not in processed_files:
        processed_files.append(file_path)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(processed_files, f, indent=2)
