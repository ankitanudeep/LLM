'''
Ankit Anudeep
Ollama Vision Chat Application
This application allows users to upload an image and ask questions about it using the Ollama Vision model
'''

import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import base64
import ollama
import threading

MODEL = "llava"

def encode_image_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

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

def on_enter_key(event):
    query = query_entry.get()
    if not query.strip():
        return

    image_path = image_label.image_path
    if not image_path:
        status_text.set("Please upload an image first.")
        return

    status_text.set("Sending request to model...")
    query_entry.delete(0, tk.END)

    def stream_worker():
        try:
            image_base64 = encode_image_base64(image_path)
            output_text.insert(tk.END, f"\n\nYou: {query}\n", "user")

            stream = ollama.chat(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": query,
                        "images": [image_base64]
                    }
                ],
                stream=True
            )

            output_text.insert(tk.END, "AI: ", "bot")
            for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                output_text.insert(tk.END, content)
                output_text.see(tk.END)

            status_text.set("Response complete.")
        except Exception as e:
            output_text.insert(tk.END, f"\n[Error: {e}]\n", "error")
            status_text.set("Failed to get response.")

    threading.Thread(target=stream_worker, daemon=True).start()

def upload_image():
    filepath = filedialog.askopenfilename(
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")]
    )
    if filepath:
        img = Image.open(filepath)
        img.thumbnail((300, 300))
        photo = ImageTk.PhotoImage(img)

        image_label.config(image=photo)
        image_label.image = photo
        image_label.image_path = filepath
        status_text.set("Image uploaded successfully.")

# GUI setup
root = tk.Tk()
root.title("Ollama Vision Chat")
root.geometry("600x750")

upload_btn = tk.Button(root, text="Upload Image", command=upload_image)
upload_btn.pack(pady=10)

image_label = tk.Label(root)
image_label.image_path = None
image_label.pack(pady=10)

query_entry = tk.Entry(root, font=("Segoe UI", 12))
query_entry.pack(fill=tk.X, padx=10, pady=5)
query_entry.bind("<Return>", on_enter_key)

output_text = tk.Text(root, wrap=tk.WORD, height=20, font=("Segoe UI", 11))
output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
output_text.tag_config("user", foreground="blue", font=("Segoe UI", 11, "bold"))
output_text.tag_config("bot", foreground="green", font=("Segoe UI", 11, "bold"))
output_text.tag_config("error", foreground="red")

status_text = tk.StringVar()
status_label = tk.Label(root, textvariable=status_text, fg="blue")
status_label.pack(pady=5)

# Pull model in background
threading.Thread(target=ensure_model_available, args=(MODEL,), daemon=True).start()

root.mainloop()
