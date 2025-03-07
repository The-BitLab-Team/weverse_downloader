import json
import os
import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog

def extract_video_url(logs):
    """
    Extrai o link direto do vídeo a partir dos logs de rede.
    Procura por links contendo .m3u8 ou .mp4.
    """
    for log in logs:
        message = json.loads(log['message'])
        try:
            url = message['message']['params']['request']['url']
            if '.m3u8' in url or '.mp4' in url:
                return url
        except KeyError:
            continue
    return None

def download_video(video_url, output_file):
    """
    Baixa o vídeo usando ffmpeg.
    """
    print(f"Baixando vídeo de: {video_url}")
    command = f'ffmpeg -i "{video_url}" -c copy "{output_file}"'
    os.system(command)
    print(f"Download concluído. Arquivo salvo como {output_file}")

def main(video_page_url, output_file):
    # Configuração do navegador para capturar logs de rede
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Executa o Chrome em modo headless
    service = Service('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')  # Atualize com o caminho do chromedriver
    chrome_options.add_experimental_option("perfLoggingPrefs", {"enableNetwork": True})
    driver = webdriver.Chrome(service=service, options=chrome_options, desired_capabilities=caps)


    try:
        # Acessa a página do vídeo
        driver.get(video_page_url)
        print("Carregando página...")
        time.sleep(10)  # Ajuste o tempo conforme necessário para o carregamento

        # Captura os logs de desempenho (tráfego de rede)
        logs = driver.get_log('performance')
        video_url = extract_video_url(logs)

        if video_url:
            print(f"Link direto encontrado: {video_url}")
            download_video(video_url, output_file)
        else:
            print("Não foi possível encontrar o link direto do vídeo.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        # Fecha o navegador
        driver.quit()

def start_download():
    video_page_url = url_entry.get()
    if not video_page_url:
        messagebox.showerror("Erro", "Por favor, insira a URL do vídeo.")
        return
    
    output_file = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")])
    if not output_file:
        return
    
    main(video_page_url, output_file)

# Configuração da interface gráfica
root = tk.Tk()
root.title("Weverse Downloader")

tk.Label(root, text="URL do vídeo:").pack(pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

download_button = tk.Button(root, text="Baixar Vídeo", command=start_download)
download_button.pack(pady=20)

root.mainloop()