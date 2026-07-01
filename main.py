import os
import json
import requests
from markdownify import markdownify as md
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables securely
load_dotenv()

# Initialize the Gemini Client
# This automatically picks up GEMINI_API_KEY from your environment
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json?per_page=40"
OUTPUT_DIR = "articles"
STATE_FILE = "sync_state.json"

def load_state():
    """Loads the delta tracking state from a JSON file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    """Saves the delta tracking state to a JSON file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def upload_to_gemini(filepath, title):
    """Uploads a file to Google AI Studio Files API (Knowledge Base equivalent)."""
    print(f"Uploading {filepath} to Google Gemini...")
    
    # Upload to Gemini's File API 
    uploaded_file = client.files.upload(
        file=filepath,
        config=types.UploadFileConfig(
            display_name=title,
            mime_type="text/plain" # Markdown is processed as plain text
        )
    )
    
    print(f"Successfully uploaded: {uploaded_file.name} ({uploaded_file.uri})")
    return uploaded_file.name

def run_sync_job():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    state = load_state()
    counts = {"added": 0, "updated": 0, "skipped": 0}

    print("Fetching articles from Zendesk API...")
    response = requests.get(API_URL)
    articles = response.json().get("articles", [])

    for article in articles:
        article_id = str(article.get("id"))
        updated_at = article.get("updated_at")
        title = article.get("title", "Untitled")
        body_html = article.get("body", "")
        url = article.get("html_url", "")

        if not body_html:
            continue

        # DELTA LOGIC: Check if the article is new or has a newer timestamp
        if article_id in state and state[article_id] == updated_at:
            counts["skipped"] += 1
            continue

        is_update = article_id in state

        # Convert to Markdown
        markdown_content = md(body_html, heading_style="ATX")

        # Inject BOTH URL and Last-Modified timestamp into the file header
        final_content = f"# {title}\n\n**Article URL:** {url}\n**Last-Modified:** {updated_at}\n\n{markdown_content}"
        
        filename = os.path.join(OUTPUT_DIR, f"{article_id}.md")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_content)

        # Upload to Gemini Files API
        try:
            upload_to_gemini(filename, title)
            # Only update state if upload succeeds
            state[article_id] = updated_at
            
            if is_update:
                counts["updated"] += 1
            else:
                counts["added"] += 1
                
        except Exception as e:
            print(f"Failed to upload {filename}: {e}")

    save_state(state)
    
    # Required logging output for the daily job
    # For Gemini, 1 File = 1 Semantic Chunk in the context window
    print("\n--- Daily Sync Job Complete ---")
    print(f"Files Added:   {counts['added']}")
    print(f"Files Updated: {counts['updated']}")
    print(f"Files Skipped: {counts['skipped']}")
    total_embedded = counts['added'] + counts['updated']
    print(f"Chunks Embedded: {total_embedded} (Using 1:1 file-to-chunk ratio via native ingestion)")

if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY is missing from .env")
    else:
        run_sync_job()