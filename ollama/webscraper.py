'''
Ankit Anudeep
ollama/webscraper.py
This module provides functionality to scrape company websites and generate brochures using the Ollama LLM.
'''

import gradio as gr
import requests
from bs4 import BeautifulSoup
import ollama
import logging
import re
import json
from markdown import markdown

# Set your model name
MODEL = "llama3.2"

# User-Agent header for website scraping
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

# Log errors if needed
logging.basicConfig(level=logging.WARNING)


# SYSTEM PROMPTS
link_system_prompt = """
    You are provided with a list of links found on a webpage.
    Decide which links are most relevant for a company brochure:
    - About page
    - Company info
    - Careers/Jobs
    - Customers
    - Blog/Team

    Respond only in JSON format like:
    {
    "links": [
        {"type": "about page", "url": "https://site.com/about"},
        {"type": "careers page", "url": "https://site.com/jobs"}
    ]
    }
"""

brochure_system_prompt = """
    You are an assistant that analyzes the contents of company webpages 
    and creates a short brochure for prospective customers, investors, and recruits.

    You MUST use the exact company name provided.
    Respond in markdown format.

    Include:
    - Company mission & culture
    - Customers (if available)
    - Careers/jobs info (if found)
    - Services or products offered
"""


# Utility class
class Website:
    def __init__(self, url):
        self.url = url
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        self.title = soup.title.string.strip() if soup.title else "No title found"

        if soup.body:
            for tag in soup.body(["script", "style", "img", "input", "noscript"]):
                tag.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)
        else:
            self.text = ""

        raw_links = [link.get('href') for link in soup.find_all('a')]
        self.links = [link for link in raw_links if link and not link.startswith("mailto:")]

    def get_contents(self):
        return f"Title: {self.title}\n\n{self.text}\n\n"


# URL check
def is_url_reachable(url, timeout=5):
    try:
        return requests.head(url, timeout=timeout).status_code < 400
    except requests.RequestException:
        return False


# Extract JSON from model response
def extract_json_from_text(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else None


# Build user prompt to extract relevant links
def build_link_prompt(website):
    prompt = f"Here is a list of links found on {website.url}:\n"
    prompt += "\n".join(website.links)
    return prompt


# Ask model to choose relevant pages
def get_links(url):
    website = Website(url)
    user_prompt = build_link_prompt(website)

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": link_system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        json_text = extract_json_from_text(response['message']['content'])
        return json.loads(json_text) if json_text else None
    except Exception as e:
        logging.warning(f"Link extraction failed: {e}")
        return None


# Collect page content from main + selected links
def get_all_website_content(url):
    try:
        website = Website(url)
        result = f"Main Page:\n{website.get_contents()}"

        links_json = get_links(url)
        if links_json:
            for link in links_json["links"]:
                if is_url_reachable(link["url"]):
                    subpage = Website(link["url"])
                    result += f"\n\n---\n{link['type'].title()}:\n{subpage.get_contents()}"
        return result[:5000]  # keep within model limits
    except Exception as e:
        logging.warning(f"Error scraping website content: {e}")
        return ""


# Combine prompt with actual company name
def build_brochure_prompt(company_name, url):
    content = get_all_website_content(url)
    if not content:
        return None

    prompt = f"""The company name is: {company_name}
        You MUST use this exact name in the brochure.
        Below are webpages from their site. Use this content to create a professional brochure:
        {content}
        """
    return prompt

# Gradio streaming
def stream_brochure(company_name, url):
    if not is_url_reachable(url):
        yield "Error: Website is not reachable."
        return

    prompt = build_brochure_prompt(company_name, url)
    if not prompt:
        yield "Error: Could not scrape website content."
        return

    try:
        stream = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": brochure_system_prompt},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
    except Exception as e:
        yield f"Error: LLM request failed: {str(e)}"
        return

    response = ""
    for chunk in stream:
        content = chunk.get("message", {}).get("content", "")
        if content:
            response += content.replace("```", "")
            yield markdown(response)


# Gradio interface
demo = gr.Interface(
    fn=stream_brochure,
    inputs=[
        gr.Textbox(label="Company Name", placeholder="e.g., HuggingFace"),
        gr.Textbox(label="Company Website URL", placeholder="e.g., https://huggingface.co")
    ],
    outputs=gr.Markdown(label="📄 Streaming Brochure"),
    title="AI-Powered Company Brochure Generator",
    description="Enter a company name and its website. This tool scrapes the content and uses an LLM to generate a streaming brochure.",
    allow_flagging="never"
)

if __name__ == "__main__":
    demo.launch()
