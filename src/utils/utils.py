import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path: str = 'variables.json') -> Dict[str, Any]:
    """
    Loads configuration from a JSON file.

    Parameters
    ----------
    - config_path: str The path to the configuration file.

    Returns
    -------
    - Dict[str, Any] A dictionary containing the configuration variables.
    """
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
            if not config_data:
                logging.error("Configuration file is empty.")
                return {}
            return config_data
    except FileNotFoundError:
        logging.error(f"Configuration file not found at {config_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {config_path}")
        return {}

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
        with open(path, 'r') as f:
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
        with open(path, 'w') as f:
            json.dump(processed_files, f, indent=2)
