import os
import logging
import argparse
from src.utils import load_config
from src.flash_gen import get_genai_client, process_files_in_folder, load_system_prompt
from src.anki_uploader import load_flashcards, create_anki_deck, upload_deck_to_anki, get_existing_decks

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine the absolute path of the script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set the source directory for PDFs to the current working directory
PDF_SOURCE_DIR = os.getcwd()

def main():
    """
    Main function to run the complete flashcard generation and Anki upload workflow.
    """
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Generate Anki flashcards from PDFs.")
    parser.add_argument(
        '--no-skip', 
        dest='skip_processed_files', 
        action='store_false',
        help="Process all files, even if they have been processed before."
    )
    parser.add_argument(
        '--flashcards',
        dest='flashcards_file',
        type=str,
        help="Path to an existing JSON file with flashcards. Skips PDF generation if provided."
    )
    parser.set_defaults(skip_processed_files=True)
    args = parser.parse_args()

    # Load configuration with defaults and local overrides
    config = load_config()

    if args.flashcards_file:
        cwd_path = os.path.abspath(args.flashcards_file)
        files_dir_path = os.path.join(os.getcwd(), 'files', args.flashcards_file)
        
        if os.path.exists(cwd_path):
            flashcard_path = cwd_path
        elif os.path.exists(files_dir_path):
            flashcard_path = files_dir_path
        else:
            flashcard_path = cwd_path
            
        logging.info(f"Skipping PDF generation. Using provided flashcards file: {flashcard_path}")
    else:
        # ---------------------------------------------
        # --- Part 1: Generate Flashcards from PDFs ---
        # ---------------------------------------------
        logging.info("--- Starting Flashcard Generation ---")
        # Configure parameters    
        genai_model = config["GENAI_MODEL"]
        math_prompt_path = os.path.join(os.path.dirname(os.path.abspath(__import__('src').__file__)), 'math_prompt.md')
        flashcard_path = os.path.abspath(config["FLASHCARD_FILE_PATH"])
        processed_files_path = os.path.abspath(config["PROCESSED_FILES_PATH"])
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
        process_files_in_folder(
            PDF_SOURCE_DIR, 
            client, 
            genai_model, 
            system_prompt, 
            flashcard_path, 
            processed_files_path,
            skip_processed_files=args.skip_processed_files
        )
        
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
    output_path = os.path.abspath(config["ANKI_OUTPUT_PATH"])
    anki_connect_url = config["ANKICONNECT_URL"]

    if not all([deck_name, model_name, output_path, anki_connect_url]):
        logging.error("Anki configuration details are missing from variables.json.")
        return

    # --- Interactive Deck Selection ---
    print("\n" + "="*40)
    print("Anki Deck Selection")
    print("="*40)
    existing_decks = get_existing_decks(anki_connect_url)
    
    if existing_decks:
        print("Existing Anki Decks:")
        for i, deck in enumerate(existing_decks, 1):
            print(f"  {i}. {deck}")
        print(f"  {len(existing_decks) + 1}. Create a new deck")
        print("-" * 40)
        
        while True:
            try:
                choice = input(f"Select a deck (1-{len(existing_decks) + 1}) or type a deck name: ").strip()
                if not choice:
                    continue
                if choice.isdigit():
                    idx = int(choice)
                    if 1 <= idx <= len(existing_decks):
                        deck_name = existing_decks[idx - 1]
                        break
                    elif idx == len(existing_decks) + 1:
                        new_deck = input("Enter new deck name: ").strip()
                        if new_deck:
                            deck_name = new_deck
                            break
                        else:
                            print("Deck name cannot be empty.")
                    else:
                        print("Invalid selection. Please try again.")
                else:
                    deck_name = choice
                    break
            except (KeyboardInterrupt, EOFError):
                print("\nOperation cancelled by user.")
                return
    else:
        try:
            new_deck = input(f"Enter deck name to upload (default: {deck_name}): ").strip()
            if new_deck:
                deck_name = new_deck
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            return
            
    print(f"\nSelected Deck: {deck_name}")
    print("="*40 + "\n")

    # Create and upload the Anki deck
    create_anki_deck(flashcards, deck_name, model_name, output_path)
    
    if os.path.exists(output_path):
        upload_deck_to_anki(output_path, anki_connect_url)
    else:
        logging.error(f"Anki deck file was not created at '{output_path}'.")
    
    logging.info("--- Anki Deck Creation and Upload Finished ---")

if __name__ == "__main__":
    main()
