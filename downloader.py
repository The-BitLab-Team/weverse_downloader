import json
import os
import time
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_video_url(logs):
    """
    Extracts the direct video URL from network logs.
    Looks for URLs containing .m3u8 or .mp4.
    """
    for log in logs:
        try:
            message = json.loads(log['message'])
            url = message.get('message', {}).get('params', {}).get('request', {}).get('url', '')
            if url and ('.m3u8' in url or '.mp4' in url):
                return url
        except (KeyError, json.JSONDecodeError):
            continue
    return None

def download_video(video_url, output_file):
    """
    Downloads the video using ffmpeg.
    """
    print(f"Downloading video from: {video_url}")
    command = f'ffmpeg -i "{video_url}" -c copy "{output_file}"'
    subprocess.run(command, shell=True, check=True)
    print(f"Download completed. File saved as {output_file}")

def main(video_page_url):
    # Configure the browser to capture network logs
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Runs Chrome in headless mode
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    # Update with the correct chromedriver path
    service = Service('C:\\path\\to\\chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Navigate to the video page
        driver.get(video_page_url)
        print("Loading page...")
        
        # Wait for the page to load
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        
        # Extract the title of the video
        title = driver.title
        output_file = f"{title}.mp4"
        
        # Capture performance logs (network traffic)
        logs = driver.get_log('performance')
        video_url = extract_video_url(logs)

        if video_url:
            print(f"Direct link found: {video_url}")
            download_video(video_url, output_file)
        else:
            print("Could not find direct video URL.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the browser
        driver.quit()

def start_download():
    video_page_url = url_entry.get()
    if not video_page_url:
        messagebox.showerror("Error", "Please enter the video URL.")
        return
    
    # Run main in a separate thread to avoid UI freeze
    threading.Thread(target=main, args=(video_page_url,), daemon=True).start()

# Configuration of the GUI
root = tk.Tk()
root.title("Weverse Video Downloader")
root.geometry("500x300")  # Set the size of the window
root.config(bg="#f0f0f0")  # Set a light background color

# Create a frame for better organization
frame = tk.Frame(root, bg="#f0f0f0")
frame.pack(pady=20)

# Add title label with styling
title_label = tk.Label(frame, text="Weverse Video Downloader", font=("Helvetica", 16, "bold"), fg="#333")
title_label.grid(row=0, column=0, columnspan=2, pady=10)

# Label and entry for the URL
url_label = tk.Label(frame, text="Video URL:", font=("Helvetica", 12), bg="#f0f0f0")
url_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")

url_entry = tk.Entry(frame, width=40, font=("Helvetica", 12), borderwidth=2, relief="solid")
url_entry.grid(row=1, column=1, padx=10, pady=10)

# Button to start download
download_button = tk.Button(frame, text="Download Video", command=start_download, font=("Helvetica", 12), bg="#4CAF50", fg="white", relief="flat", width=20)
download_button.grid(row=2, column=0, columnspan=2, pady=20)

# Add padding for the overall window
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=1)

root.mainloop()
