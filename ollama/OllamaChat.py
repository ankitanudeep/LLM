'''
Ollama Chat Application
OllamaChat.py - A simple GUI application to interact with the Ollama chat model.
This application allows users to input questions and receive answers from the Ollama model.'''

import ollama
import tkinter as tk
from tkinter import ttk
import re
import threading

OLLAMA_API = "http://localhost:11434/api/chat" # Ollama API endpoint
MODEL = "gemma3:1b"
#MODEL = "deepseek-r1:1.5b"

conversation_history = []

def ensure_model_available(model_name):
    try:
        # Get list of all models already pulled
        existing_models = [model['model'] for model in ollama.list()['models']]
        if model_name not in existing_models:
            print(f"Model '{model_name}' not found. Pulling now...")
            ollama.pull(model=model_name)
            print(f"Model '{model_name}' pulled successfully.")
    except Exception as e:
        print(f"Failed to ensure model availability: {e}")


ensure_model_available(MODEL)

def handle_keypress(event):
    if event.state & 0x1:  # Check if Shift is pressed
        return
    else:
        #display_answer()
        display_answer_stream()
        return 'break'
		
def display_answer(event=None):
    question_text['state'] = 'disabled'
    question_text['bg'] = '#F0F0F0'
    status_label.config(text="Looking for an answer...")
    root.update()

    # Get question text and prepare message
    question = question_text.get("1.0", tk.END).strip()
    if question:
        # Append the user's question to the conversation history
        conversation_history.append({"role": "user", "content": question})

        # Pass the entire conversation history to Ollama
        try:
            # Get the answer
            response = ollama.chat(model=MODEL, messages=conversation_history)
            answer = response["message"]["content"]

            # Append the assistant's answer to the conversation history
            conversation_history.append({"role": "assistant", "content": answer})

            # Update the text widget with the answer
            answer_text.configure(state='normal')
            answer_text.delete(1.0, tk.END)
            answer_text.insert(tk.END, answer)
            answer_text.configure(state='disabled')

            status_label.config(text="Answered")
        except Exception as e:
            answer_text.configure(state='normal')
            answer_text.delete(1.0, tk.END)
            answer_text.insert(tk.END, f"Error: {str(e)}")
            answer_text.configure(state='disabled')
            status_label.config(text="Error")
    else:
        # If empty question string was received
        answer_text.configure(state='normal')
        answer_text.delete(1.0, tk.END)
        answer_text.insert(tk.END, "Please enter a question.")
        answer_text.configure(state='disabled')
        status_label.config(text="")

    # Re-enable question input and restore normal background
    question_text['state'] = 'normal'
    question_text['bg'] = 'white'
    root.update()
	
def display_answer_stream(event=None):
    def run_chat():
        question_text['state'] = 'disabled'
        question_text['bg'] = '#F0F0F0'
        status_label.config(text="Looking for an answer...")
        root.update()

        question = question_text.get("1.0", tk.END).strip()
        if question:
            conversation_history.append({"role": "user", "content": question})

            try:
                answer_text.configure(state='normal')
                answer_text.delete(1.0, tk.END)

                response_stream = ollama.chat(
                    model=MODEL,
                    messages=conversation_history,
                    stream=True
                )

                full_response = ""
                for chunk in response_stream:
                    delta = chunk.get("message", {}).get("content", "")
                    delta = re.sub(r'</?think>', '', delta)
                    full_response += delta
                    answer_text.insert(tk.END, delta)
                    answer_text.see(tk.END)
                    answer_text.update()

                conversation_history.append({"role": "assistant", "content": full_response})

                answer_text.configure(state='disabled')
                status_label.config(text="Answered")
            except Exception as e:
                answer_text.configure(state='normal')
                answer_text.delete(1.0, tk.END)
                answer_text.insert(tk.END, f"Error: {str(e)}")
                answer_text.configure(state='disabled')
                status_label.config(text="Error")
        else:
            answer_text.configure(state='normal')
            answer_text.delete(1.0, tk.END)
            answer_text.insert(tk.END, "Please enter a question.")
            answer_text.configure(state='disabled')
            status_label.config(text="")

        # Clear the question box after processing
        question_text['state'] = 'normal'
        question_text.delete(1.0, tk.END)  # <-- Add this line
        question_text['bg'] = 'white'
        root.update()

    threading.Thread(target=run_chat).start()

def remove_all():
    """Clears the conversation history and resets the interface."""
    global conversation_history
    conversation_history = []  # Clear conversation history

    # Reset text widgets
    question_text.delete(1.0, tk.END)
    answer_text.configure(state='normal')
    answer_text.delete(1.0, tk.END)
    answer_text.insert(tk.END, "Your answer will appear here.")
    answer_text.configure(state='disabled')

    # Reset status label
    status_label.config(text="")
	
# Create the main window
root = tk.Tk()
root.title("Ollama with GUI")
root.geometry("500x800")

# Create and configure the Questions window
question_frame = ttk.LabelFrame(root, text="Questions", padding=(10, 10))
question_frame.pack(fill="both", expand=True, padx=10, pady=10)

question_label = ttk.Label(question_frame, text="Enter your question:")
question_label.pack(anchor="w", pady=5)

# Replace Entry with Text widget for questions
question_text = tk.Text(question_frame, wrap=tk.WORD, width=50, height=4)
question_text.pack(anchor="w", pady=5)
question_text.bind("<Return>", handle_keypress)

# Add status label
status_label = ttk.Label(question_frame, text="")
status_label.pack(anchor="w", pady=5)

# Add Remove All button
remove_all_button = ttk.Button(question_frame, text="Remove All", command=remove_all)
remove_all_button.pack(anchor="e", pady=5)

# Create and configure the Answers window
answer_frame = ttk.LabelFrame(root, text="Answer", padding=(10, 10))
answer_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Create a frame to hold the text widget and scrollbar
text_frame = ttk.Frame(answer_frame)
text_frame.pack(fill="both", expand=True)

# Create the text widget and scrollbar
answer_text = tk.Text(text_frame, wrap=tk.WORD, width=70, height=100)
scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=answer_text.yview)
answer_text.configure(yscrollcommand=scrollbar.set)

# Pack the text widget and scrollbar
answer_text.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Set initial text and disable editing
answer_text.insert(tk.END, "Your answer will appear here.")
answer_text.configure(state='disabled')

# Run the main event loop
root.mainloop()
