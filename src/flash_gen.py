import os
import json
import logging
from typing import List, Dict, Any

import pdfplumber
from openai import OpenAI

from src.utils import get_processed_files, add_processed_file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_openai_client(base_url: str) -> OpenAI:
    """
    Initializes and returns the OpenAI client.

    Parameters
    ----------
    - base_url: str
        The base URL for the OpenAI API.

    Returns
    -------
    - OpenAI
        An instance of the OpenAI client.
        
    Raises
    ------
    - ValueError
        If the DEEPSEEK_API_KEY environment variable is not set.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set.")

    return OpenAI(api_key=api_key, base_url=base_url)

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

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts all text content from a given PDF file.

    Parameters
    ----------
    - pdf_path: str
        The full path to the PDF file.

    Returns
    -------
    - str
        The concatenated text content from all pages of the PDF.
    """
    full_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
    except Exception as e:
        logging.error(f"Error reading PDF file {pdf_path}: {e}")
        return ""
    return "\n".join(full_text)

def generate_flashcards_from_text(
        client: OpenAI,
        model: str,
        system_prompt: str,
        text: str) -> List[Dict[str, str]]:
    """
    Generates flashcards from text using the DeepSeek API.

    Parameters
    ----------
    - client: OpenAI
        The configured OpenAI client.
    - model: str
        The deepseek version (chat | reasoner)
    -system_prompt: str
        The subject specific prompt.
    - text: str
        The text to generate flashcards from.

    Returns
    -------
    - List[Dict[str, str]]
        A list of flashcard dictionaries.
    """
    
    user_prompt = f"Generate flashcards in json format based on the following text:\n\n---\n{text}\n---"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        response_content = response.choices[0].message.content
        if response_content:
            data = json.loads(response_content)
            return data.get("flashcards", [])
        else:
            logging.error("Received empty response content from API.")
            return []
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from API response: {e}")
        logging.error(f"Received content: {response_content}") #type: ignore
        return []
    except Exception as e:
        logging.error(f"An API error occurred: {e}")
        return []

def process_files_in_folder(folder_path: str, client: OpenAI, model: str, system_prompt: str, flashcard_path: str, processed_files_path: str) -> None:
    """
    Scans a folder for PDF files, generates flashcards, and saves them to a JSON file.

    Parameters
    ----------
    - folder_path: str
        The path to the folder containing PDF files.
    - client: OpenAI
        The configured OpenAI client.
    - model: str
        The deepseek version (chat | reasoner)
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

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, filename)
            if pdf_path in processed_files:
                logging.warning(f"'{filename}' has already been processed. Skipping.")
                continue

            logging.info(f"Processing '{filename}'...")

            document_text = extract_text_from_pdf(pdf_path)
            if not document_text:
                logging.warning(f"Could not extract text from '{filename}', skipping.")
                continue
            
            logging.info(f"Generating flashcards for '{filename}'...")
            flashcards = generate_flashcards_from_text(client, model, system_prompt,  document_text)
            
            if flashcards:
                all_flashcards.extend(flashcards)
                add_processed_file(processed_files_path, pdf_path)
                logging.info(f"Successfully generated {len(flashcards)} flashcards from '{filename}'.")
            else:
                logging.warning(f"No flashcards were generated for '{filename}'.")

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
