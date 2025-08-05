'''
# Ankit Anudeep
# openai/websitesummarizer.py
# This module provides functionality to scrape company websites and generate summaries using OpenAI's LLM.
# It uses the OpenAI API to summarize the content of a webpage in markdown format.
# It is designed to be used with Gradio for a user-friendly interface.
# It handles website scraping, content extraction, and LLM interaction.
'''

import requests
import gradio as gr
from bs4 import BeautifulSoup
from openai import OpenAI

OPENAI_API_KEY="your-openai-api-key"
openai = OpenAI(api_key=OPENAI_API_KEY)

system_prompt = """You are an assistant that analyzes the contents of a website \
and provides a short summary, ignoring text that might be navigation related. \
Respond in markdown."""

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

class Website:
    def __init__(self, url):
        self.url = url
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        self.title = soup.title.string if soup.title else "No title found"
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        self.text = soup.body.get_text(separator="\n", strip=True) if soup.body else ""

def user_prompt_for(website):
    user_prompt = f"You are looking at a website titled {website.title}"
    user_prompt += "\nThe contents of this website is as follows; \
    please provide a short summary of this website in markdown. \
    If it includes news or announcements, then summarize these too.\n\n"
    user_prompt += website.text
    return user_prompt

def messages_for(website):
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_for(website)}
    ]

def summarize_stream(url):
    if not url.strip():
        yield "Please enter a valid URL."
        return

    try:
        website = Website(url)
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_for(website),
            stream=True
        )
        partial = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                partial += chunk.choices[0].delta.content
                yield partial
    except Exception as e:
        yield f"Error: {str(e)}"


with gr.Blocks() as demo:
    gr.Markdown("# Website Summarizer")
    gr.Markdown("Get a quick markdown summary of any webpage using GPT-4o-mini.")

    with gr.Row():
        with gr.Column(scale=1):
            url_input = gr.Textbox(label="Website URL", placeholder="https://example.com")
            start_button = gr.Button("Summarize", variant="primary")
            clear_button = gr.Button("Clear", variant="secondary")

        with gr.Column(scale=2):
            output = gr.Markdown(label="Summary Output")

    # Logic to disable/enable button while generating
    def wrap_summarizer(url):
        yield gr.update(interactive=False), ""  # Clear output and disable button
        for output_chunk in summarize_stream(url):
            yield gr.update(), output_chunk
        yield gr.update(interactive=True), gr.update()  # Just re-enable button, don't clear output


    start_button.click(
        fn=wrap_summarizer,
        inputs=url_input,
        outputs=[start_button, output]
    )

    clear_button.click(
        fn=lambda: ("", "", gr.update(interactive=True)),
        inputs=None,
        outputs=[url_input, output, start_button]
    )

if __name__ == "__main__":
    demo.launch()
