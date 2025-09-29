import os
import logging
from src.utils import load_config
from src.flash_gen import get_genai_client, process_files_in_folder, load_system_prompt
from src.anki_uploader import load_flashcards, create_anki_deck, upload_deck_to_anki

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine the absolute path of the script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set the source directory for PDFs relative to the script directory
PDF_SOURCE_DIR = SCRIPT_DIR

def main():
    """
    Main function to run the complete flashcard generation and Anki upload workflow.
    """
    # Construct absolute path for the configuration file
    config_path = os.path.join(SCRIPT_DIR, 'variables.json')
    config = load_config(config_path)

    # ---------------------------------------------
    # --- Part 1: Generate Flashcards from PDFs ---
    # ---------------------------------------------
    logging.info("--- Starting Flashcard Generation ---")
    # Configure parameters    
    genai_model = config["GENAI_MODEL"]
    math_prompt_path = os.path.join(SCRIPT_DIR, config["MATH_PROMPT"])
    flashcard_path = os.path.join(SCRIPT_DIR, config["FLASHCARD_FILE_PATH"])
    processed_files_path = os.path.join(SCRIPT_DIR, config["PROCESSED_FILES_PATH"])
    system_prompt = load_system_prompt(math_prompt_path)

    if not genai_model:
        logging.error("GENAI_MODEL is not specified in variables.json.")
        return
    if not system_prompt:
        logging.error(f"Prompt file '{math_prompt_path}' is empty or could not be read.")
        return

    try:
        client = get_genai_client()
    except ValueError as e:
        logging.error(f"Error initializing OpenAI client: {e}")
        return
    # Begin processing files
    process_files_in_folder(PDF_SOURCE_DIR, client, genai_model, system_prompt, flashcard_path, processed_files_path)
    
    logging.info("--- Flashcard Generation Finished ---")

    # -------------------------------------------
    # --- Part 2: Create and Upload Anki Deck ---
    # -------------------------------------------
    logging.info("--- Starting Anki Deck Creation and Upload ---")

    # Load flashcards and configure parameters
    flashcards = load_flashcards(flashcard_path)
    if not flashcards:
        logging.warning("No flashcards found in the file. Skipping Anki deck creation.")
        return

    deck_name = config["ANKI_DECK_NAME"]
    model_name = config["ANKI_MODEL_NAME"]
    output_path = os.path.join(SCRIPT_DIR, config["ANKI_OUTPUT_PATH"])
    anki_connect_url = config["ANKICONNECT_URL"]

    if not all([deck_name, model_name, output_path, anki_connect_url]):
        logging.error("Anki configuration details are missing from variables.json.")
        return

    # Create and upload the Anki deck
    create_anki_deck(flashcards, deck_name, model_name, output_path)
    
    if os.path.exists(output_path):
        upload_deck_to_anki(output_path, anki_connect_url)
    else:
        logging.error(f"Anki deck file was not created at '{output_path}'.")
    
    logging.info("--- Anki Deck Creation and Upload Finished ---")

if __name__ == "__main__":
    main()
