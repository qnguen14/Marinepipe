import os
import requests
from markdownify import markdownify as md

# Zendesk API endpoint with per_page=40 to safely hit the ">= 30" requirement
API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json?per_page=40"
OUTPUT_DIR = "articles"

def fetch_and_convert_articles():
    # Create the output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created directory: {OUTPUT_DIR}")

    print(f"Fetching articles from {API_URL}...")
    response = requests.get(API_URL)
    
    if response.status_code != 200:
        print(f"Error fetching data! Status code: {response.status_code}")
        return

    data = response.json()
    articles = data.get("articles", [])
    
    print(f"Found {len(articles)} articles. Processing...")

    count = 0
    for article in articles:
        article_id = article.get("id")
        title = article.get("title", "Untitled")
        body_html = article.get("body", "")
        url = article.get("html_url", "")
        
        # Skip articles with empty bodies
        if not body_html:
            continue

        # Convert HTML to clean Markdown (ATX style uses # for headers)
        markdown_content = md(body_html, heading_style="ATX")
        
        # Inject the Title and URL at the top of the Markdown file
        # This is crucial so the AI has the URL to cite in the final test
        final_content = f"# {title}\n\n**Article URL:** {url}\n\n{markdown_content}"
        
        # Save to file as <article_id>.md
        filename = os.path.join(OUTPUT_DIR, f"{article_id}.md")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        print(f"Saved: {filename} - {title}")
        count += 1

    print(f"\nSuccess! Scraped and converted {count} articles to Markdown in the '{OUTPUT_DIR}' folder.")

if __name__ == "__main__":
    fetch_and_convert_articles()