import json
import logging
import os
import hashlib
from typing import List, Dict, Any

import genanki
import requests

from src.utils import load_config

def get_deterministic_id(name: str) -> int:
    """Generates a deterministic integer ID from a string using SHA256."""
    return int(hashlib.sha256(name.encode('utf-8')).hexdigest(), 16) % (10**10)

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

def get_existing_decks(anki_connect_url: str) -> List[str]:
    """
    Fetches the list of existing deck names from Anki using AnkiConnect.
    
    Parameters
    ----------
    - anki_connect_url: str The URL of the AnkiConnect server.
    
    Returns
    -------
    - List[str] A list of deck names.
    """
    request_payload = {
        "action": "deckNames",
        "version": 6
    }
    try:
        response = requests.post(anki_connect_url, json=request_payload, timeout=3)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("error") is None:
            return response_data.get("result", [])
    except Exception as e:
        logging.warning(f"Failed to fetch existing decks from AnkiConnect: {e}")
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
        model_id=get_deterministic_id(model_name),
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
        deck_id=get_deterministic_id(deck_name),
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

def invoke_anki_connect(anki_connect_url: str, action: str, **params) -> Any:
    """Helper function to invoke AnkiConnect API."""
    request_payload = {
        "action": action,
        "version": 6,
        "params": params
    }
    try:
        response = requests.post(anki_connect_url, json=request_payload)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("error") is not None:
            raise Exception(response_data["error"])
        return response_data.get("result")
    except Exception as e:
        logging.error(f"AnkiConnect error during {action}: {e}")
        return None

def add_notes_to_anki(flashcards: List[Dict[str, Any]], deck_name: str, model_name: str, anki_connect_url: str):
    """
    Adds notes directly to Anki using AnkiConnect, allowing duplicates.
    """
    if not flashcards:
        logging.warning("No flashcards provided to upload.")
        return

    # 1. Ensure Deck exists
    invoke_anki_connect(anki_connect_url, "createDeck", deck=deck_name)

    # 2. Ensure Model exists
    existing_models = invoke_anki_connect(anki_connect_url, "modelNames")
    if existing_models is not None and model_name not in existing_models:
        logging.info(f"Creating new Anki model: {model_name}")
        invoke_anki_connect(
            anki_connect_url, 
            "createModel", 
            modelName=model_name,
            inOrderFields=["Front", "Back", "Extra"],
            cardTemplates=[
                {
                    "Name": "Card 1",
                    "Front": "{{Front}}",
                    "Back": "{{FrontSide}}<hr id=\"answer\">{{Back}}<br><br><small>{{Extra}}</small>"
                }
            ],
            css=".card { font-family: arial; font-size: 20px; text-align: center; color: black; background-color: white; }"
        )

    # 3. Add Notes
    notes = []
    for card in flashcards:
        notes.append({
            "deckName": deck_name,
            "modelName": model_name,
            "fields": {
                "Front": card.get('front', ''),
                "Back": card.get('back', ''),
                "Extra": card.get('extra', '')
            },
            "tags": card.get('tags', []),
            "options": {
                "allowDuplicate": True
            }
        })

    result = invoke_anki_connect(anki_connect_url, "addNotes", notes=notes)
    if result:
        logging.info(f"Successfully added {len([r for r in result if r is not None])} notes to Anki.")
    else:
        logging.error("Failed to add notes to Anki.")

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
        add_notes_to_anki(flashcards, deck_name, model_name, anki_connect_url)

if __name__ == "__main__":
    main()
