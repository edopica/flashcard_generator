import os
import pathlib
import json
import logging
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.utils import get_processed_files, add_processed_file

class Flashcard(BaseModel):
    """
    Data model for a single flashcard.
    """
    front: str
    back: str
    extra: str
    tags: List[str]

class FlashcardDeck(BaseModel):
    """
    Data model for a deck of flashcards.
    """
    flashcards: List[Flashcard]


def get_genai_client(api_key: Optional[str] = None) -> genai.Client:
    """
    Initializes and returns the Google-GenAI client.

    Parameters
    ----------
    - api_key: Optional[str]
        Optional key that overrides the one stored as environment variable

    Returns
    -------
    - genai.Client
        An instance of the genai client.
        
    Raises
    ------
    - ValueError
        If the GEMINI_API_KEY environment variable is not set.
    """
    if api_key:
        return genai.Client(api_key=api_key)
        
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    return genai.Client(api_key=api_key)

def load_system_prompt(prompt_path: str) -> str:
    """
    Loads the system prompt from a text file.

    Parameters
    ----------
    - prompt_path: str
        The path to the prompt file.

    Returns
    -------
    - str
        The content of the prompt file.
    """
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Prompt file not found at '{prompt_path}'.")
        return ""

def generate_flashcards_from_pdf(
        client: genai.Client,
        model: str,
        system_prompt: str,
        filepath: pathlib.Path) -> List[Dict[str, Any]]:
    """
    Generates flashcards from a PDF file using the Gemini API.

    Parameters
    ----------
    - client: genai.Client
        The configured Google-GenAI client.
    - model: str
        The Gemini model to use for generation.
    - system_prompt: str
        The subject-specific prompt for the model.
    - filepath: pathlib.Path
        The path to the PDF file to process.

    Returns
    -------
    - List[Dict[str, Any]]
        A list of flashcard dictionaries.
    """
    
    user_prompt = "Generate flashcards in json format based on the following document:"
    response = None
    try:
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=FlashcardDeck,
            ),
            contents=[
                types.Part.from_bytes(
                    data=filepath.read_bytes(),
                    mime_type='application/pdf',
                ),
                user_prompt
            ]
        )
        
        parsed_response: Optional[FlashcardDeck] = response.parsed if isinstance(response.parsed, FlashcardDeck) else None
        if parsed_response and parsed_response.flashcards:
            return [card.model_dump() for card in parsed_response.flashcards]
        else:
            logging.warning("API returned a valid but empty flashcard deck.")
            if response and hasattr(response, 'text'):
                logging.warning(f"Received content: {response.text}")
            return []
            
    except Exception as e:
        logging.error(f"An API error or parsing error occurred: {e}")
        if response and hasattr(response, 'text'):
            logging.error(f"Received content: {response.text}")
        return []

def process_files_in_folder(
    folder_path: str,
    client: genai.Client,
    model: str,
    system_prompt: str,
    flashcard_path: str,
    processed_files_path: str,
    skip_processed_files: bool = True) -> None:
    """
    Scans a folder for PDF files, generates flashcards, and saves them to a JSON file.

    Parameters
    ----------
    - folder_path: str
        The path to the folder containing PDF files.
    - client: genai.Client
        The configured Google-GenAI client.
    - model: str
        The Gemini model to use for generation.
    - system_prompt: str
        The subject specific prompt.
    - flashcard_path: str
        The path to save the generated flashcards.
    - processed_files_path: str
        The path to the JSON file that tracks processed files.
    """
    all_flashcards = []
    processed_files = get_processed_files(processed_files_path)
    logging.info(f"Scanning for PDF files in '{folder_path}'...")

    # List files in folder
    folder = pathlib.Path(folder_path)
    for pdf_path in folder.glob("*.pdf"):
        if skip_processed_files and str(pdf_path) in processed_files:
            logging.warning(f"'{pdf_path.name}' has already been processed. Skipping.")
            continue
        
        logging.info(f"Generating flashcards for '{pdf_path.name}'...")
        flashcards = generate_flashcards_from_pdf(client, model, system_prompt, pdf_path)

        if flashcards:
            all_flashcards.extend(flashcards)
            add_processed_file(processed_files_path, str(pdf_path))
            logging.info(f"Successfully generated {len(flashcards)} flashcards from '{pdf_path.name}'.")
        else:
            logging.warning(f"No flashcards were generated for '{pdf_path.name}'.")
    
    if not all_flashcards:
        logging.info("No new flashcards were generated.")
        return

    output_dir = os.path.dirname(flashcard_path)
    os.makedirs(output_dir, exist_ok=True)
    
    output_data = {"flashcards": all_flashcards}

    try:
        with open(flashcard_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logging.info(f"Success! All flashcards saved to '{flashcard_path}'.")
    except IOError as e:
        logging.error(f"Error writing to output file '{flashcard_path}': {e}")
