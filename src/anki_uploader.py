import json
import logging
import os
from typing import List, Dict, Any

import genanki
import requests

from src.utils import load_config

def load_flashcards(file_path: str) -> List[Dict[str, Any]]:
    """
    Loads flashcards from a JSON file.

    Parameters
    ----------
    - file_path: str The path to the flashcards JSON file.

    Returns
    -------
    - List[Dict[str, Any]] A list of flashcard dictionaries.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("flashcards", [])
    except FileNotFoundError:
        logging.error(f"Flashcard file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {file_path}")
        return []

def create_anki_deck(flashcards: List[Dict[str, Any]], deck_name: str, model_name: str, output_path: str):
    """
    Creates an Anki deck from a list of flashcards.

    Parameters
    ----------
    - flashcards: List[Dict[str, Any]] A list of flashcard dictionaries.
    - deck_name: str The name of the Anki deck.
    - model_name: str The name of the Anki model.
    - output_path: str The path to save the .apkg file.
    """
    if not flashcards:
        logging.warning("No flashcards provided to create a deck.")
        return

    anki_model = genanki.Model(
        model_id=abs(hash(model_name)) % (10**10),
        name=model_name,
        fields=[
            {'name': 'Front'},
            {'name': 'Back'},
            {'name': 'Extra'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '{{Front}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Back}}<br><br><small>{{Extra}}</small>',
            },
        ])

    anki_deck = genanki.Deck(
        deck_id=abs(hash(deck_name)) % (10**10),
        name=deck_name
    )

    for card in flashcards:
        anki_note = genanki.Note(
            model=anki_model,
            fields=[card.get('front', ''), card.get('back', ''), card.get('extra', '')],
            tags=card.get('tags', [])
        )
        anki_deck.add_note(anki_note)

    try:
        genanki.Package(anki_deck).write_to_file(output_path)
        logging.info(f"Successfully created Anki deck at {output_path}")
    except Exception as e:
        logging.error(f"Error writing Anki deck file: {e}")

def upload_deck_to_anki(deck_path: str, anki_connect_url: str):
    """
    Uploads an Anki deck to Anki using the AnkiConnect API.

    Parameters
    ----------
    - deck_path: str The path to the .apkg file.
    - anki_connect_url: str The URL of the AnkiConnect server.
    """
    absolute_deck_path = os.path.abspath(deck_path)
    request_payload = {
        "action": "importPackage",
        "version": 6,
        "params": {
            "path": absolute_deck_path
        }
    }

    try:
        response = requests.post(anki_connect_url, json=request_payload)
        response.raise_for_status()
        response_data = response.json()

        if response_data.get("error") is not None:
            logging.error(f"AnkiConnect error: {response_data['error']}")
        else:
            logging.info(f"Successfully uploaded deck to Anki: {deck_path}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to connect to AnkiConnect at {anki_connect_url}. Is Anki running with AnkiConnect installed? Error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during upload: {e}")

def main():
    """
    Main function to initiate the Anki deck creation and upload process.
    """
    config = load_config()
    if not config:
        logging.error("Exiting due to missing configuration.")
        return

    deck_name = config["ANKI_DECK_NAME"]
    model_name = config["ANKI_MODEL_NAME"]
    output_path = config["ANKI_OUTPUT_PATH"]
    anki_connect_url = config["ANKICONNECT_URL"]
    flashcard_file = "./files/flashcards.json"

    if not all([deck_name, model_name, output_path]):
        logging.error("Anki configuration (DECK_NAME, MODEL_NAME, ANKI_OUTPUT_PATH) is missing from variables.json.")
        return

    flashcards = load_flashcards(flashcard_file)
    if flashcards:
        create_anki_deck(flashcards, deck_name, model_name, output_path)
        if os.path.exists(output_path):
            upload_deck_to_anki(output_path, anki_connect_url)

if __name__ == "__main__":
    main()
