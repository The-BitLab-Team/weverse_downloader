import json
import os
import time
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import re

# --- Variáveis Globais para Cookies ---
COOKIES_FILE = "weverse_cookies.json" # Nome do arquivo para salvar os cookies

# --- Funções Core ---

# Mantido para referência, mas a lógica para VODs será focada em extract_video_url_for_vods
def extract_video_url_from_live_logs(logs):
    """
    Extracts a direct video URL (m3u8/mp4) from network logs, typically for live streams.
    """
    for log in logs:
        try:
            message = json.loads(log['message'])
            url = message.get('message', {}).get('params', {}).get('request', {}).get('url', '')
            if url and ('.m3u8' in url or '.mp4' in url):
                if 'weverse' in url and ('video' in url or 'stream' in url):
                    return url
        except (KeyError, json.JSONDecodeError):
            continue
    return None

def save_cookies(driver, status_callback):
    """
    Saves browser cookies to a JSON file.
    Expects the driver to be in a logged-in state on Weverse.
    """
    try:
        # Navegar para um domínio base do Weverse para garantir que os cookies corretos sejam recuperados
        # (se o driver não estiver em uma página do Weverse)
        driver.get("https://weverse.io/home") # Ou outra URL base do Weverse
        time.sleep(2) # Pequena espera para carregar a página
        
        cookies = driver.get_cookies()
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        status_callback(f"Cookies salvos em '{COOKIES_FILE}'.")
        messagebox.showinfo("Cookies", f"Cookies salvos com sucesso em '{COOKIES_FILE}'.")
    except Exception as e:
        status_callback(f"Erro ao salvar cookies: {e}")
        messagebox.showerror("Erro de Cookies", f"Não foi possível salvar os cookies: {e}")

def load_cookies(driver, status_callback):
    """
    Loads cookies from a JSON file and adds them to the browser session.
    Returns True if cookies were loaded successfully and appear to be valid, False otherwise.
    """
    if not os.path.exists(COOKIES_FILE):
        status_callback("Arquivo de cookies não encontrado.")
        print("Arquivo de cookies não encontrado.")
        return False

    try:
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        # Você precisa navegar para o domínio base antes de adicionar cookies.
        driver.get("https://weverse.io/home") # Ou qualquer URL base do Weverse para aplicar cookies
        time.sleep(2) # Pequena espera
        
        for cookie in cookies:
            # Propriedades como 'expiry' podem precisar de ajuste para o Selenium
            if 'expiry' in cookie and (isinstance(cookie['expiry'], float) or cookie['expiry'] is None):
                if cookie['expiry'] is None:
                    del cookie['expiry']
                else:
                    cookie['expiry'] = int(cookie['expiry'])
            
            # Remova chaves 'domain' e 'path' se elas causarem problemas de add_cookie
            # ou certifique-se de que correspondem ao domínio/caminho atual
            if 'domain' in cookie:
                # O Selenium adiciona cookies para o domínio atual. Evitar erros de cross-domain.
                # Se o cookie for de um subdomínio, por exemplo, '.weverse.io', ele funcionará.
                # Se for de um domínio exato que não corresponde, pode falhar.
                pass 
            if 'path' in cookie and cookie['path'] == '/':
                # Remover path='/' é seguro, o Selenium já assume '/'.
                pass
            
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Aviso: Não foi possível adicionar o cookie '{cookie.get('name', 'N/A')}': {e}")
                continue
        
        driver.refresh() # Atualiza a página para aplicar os cookies carregados
        status_callback("Cookies carregados e aplicados. Verificando login...")
        print("Cookies loaded and applied. Refreshing page.")

        # Verifica se o login foi bem-sucedido após carregar os cookies
        # Procura por elementos que indicam que o usuário está logado (ex: perfil, feed)
        try:
            WebDriverWait(driver, 10).until(
                EC.any_of(
                    EC.url_contains("weverse.io/home"),
                    EC.url_contains("weverse.io/feed"),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/my']")) # Exemplo: link para 'Meu' perfil
                )
            )
            status_callback("Login verificado via cookies. Sessão ativa.")
            print("Login verified via cookies. Session active.")
            return True
        except TimeoutException:
            status_callback("Cookies carregados, mas não foi possível verificar o login na página principal.")
            print("Cookies loaded, but login verification timed out.")
            # Assume que os cookies foram carregados, mas pode estar em uma página diferente ou demorou.
            # O VOD ainda pode carregar se os cookies forem válidos para ele.
            return True 
        
    except FileNotFoundError: # Embora já verificado acima, para segurança
        status_callback("Arquivo de cookies não encontrado.")
        return False
    except json.JSONDecodeError:
        status_callback("Erro ao ler o arquivo de cookies. O arquivo pode estar corrompido.")
        messagebox.showerror("Erro de Cookies", "Erro ao ler o arquivo de cookies. O arquivo pode estar corrompido.")
        return False
    except Exception as e:
        status_callback(f"Erro geral ao carregar cookies: {e}")
        messagebox.showerror("Erro de Cookies", f"Ocorreu um erro geral ao carregar os cookies: {e}")
        return False

def perform_weverse_login_manual(driver, status_callback):
    """
    Instrui o usuário a fazer login manualmente na janela do navegador aberta.
    Retorna True se o login for detectado como bem-sucedido, False caso contrário.
    """
    status_callback("Por favor, faça login no Weverse na janela do navegador que abriu.")
    print("Aguardando login manual na janela do navegador...")

    login_url = "https://weverse.io/login" 
    driver.get(login_url)

    # Abre a janela do navegador para o usuário fazer login manualmente
    messagebox.showinfo(
        "Login Weverse Necessário", 
        "Uma janela do navegador Chrome foi aberta. Por favor, faça login no Weverse.\n\n"
        "APÓS o login ser bem-sucedido e você ver sua página inicial (feed), "
        "clique em 'OK' nesta caixa de diálogo para continuar e salvar seus cookies para uso futuro."
    )

    # Aguarda o usuário clicar em OK e tenta verificar o login
    status_callback("Verificando status de login após interação manual...")
    # Verifique se o login foi bem-sucedido (ex: se a URL mudou para a página inicial logada)
    try:
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.url_contains("weverse.io/home"),
                EC.url_contains("weverse.io/feed"),
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/my']")) # Exemplo: link para 'Meu' perfil
            )
        )
        status_callback("Login manual detectado como bem-sucedido.")
        print("Login manual detectado como bem-sucedido.")
        # Após o login manual bem-sucedido, salve os cookies para uso futuro
        save_cookies(driver, status_callback)
        return True
    except TimeoutException:
        status_callback("Login manual não foi detectado. Tente novamente.")
        print("Login manual não foi detectado. URL atual:", driver.current_url)
        messagebox.showwarning(
            "Login Weverse", 
            "Não foi detectado que você está logado após clicar em OK. "
            "Certifique-se de que a página inicial do Weverse (com seu feed) foi carregada após o login. "
            "Por favor, tente novamente ou insira uma URL de VOD pública."
        )
        return False
    except Exception as e:
        status_callback(f"Erro inesperado ao verificar login manual: {e}")
        print(f"Erro inesperado ao verificar login manual: {e}")
        return False


def extract_video_url_for_vods(driver, status_callback):
    """
    Tenta extrair a URL de um VOD (Vídeo On Demand) do Weverse.
    Prioriza a busca em elementos DOM e depois em logs de rede.
    """
    status_callback("Tentando encontrar URL do VOD...")
    print("Tentando encontrar URL do VOD...")

    video_url = None

    # --- ESTRATÉGIA 1: Tentar encontrar URLs em tags de vídeo ou scripts ---
    try:
        # Tenta encontrar a tag <video> e seu atributo src
        video_element = WebDriverWait(driver, 15).until( # Aumentar espera
            EC.presence_of_element_located((By.CSS_SELECTOR, 'video[src]'))
        )
        video_src = video_element.get_attribute('src')
        if video_src and (video_src.startswith('http://') or video_src.startswith('https://')):
            print(f"Found video src attribute: {video_src}")
            status_callback("URL de vídeo encontrada na tag <video>.")
            return video_src
        elif video_src and video_src.startswith('blob:'):
            print("Ignorando URL blob, não é possível baixar diretamente.")
    except TimeoutException:
        print("Timeout: <video> tag not found within 15 seconds.")
    except Exception as e:
        print(f"Error finding <video> tag src: {e}")
        
    # Tenta encontrar elementos <source> dentro de <video>
    try:
        source_elements = driver.find_elements(By.CSS_SELECTOR, 'video > source[src]')
        for source in source_elements:
            src = source.get_attribute('src')
            if src and ('.m3u8' in src or '.mp4' in src or '.mpd' in src):
                print(f"Found video src in <source> tag: {src}")
                status_callback("URL de vídeo encontrada na tag <source>.")
                return src
    except Exception as e:
        print(f"Error finding <source> tag src: {e}")

    # --- ESTRATÉGIA 2: Análise de logs de desempenho (mais comum para streaming adaptativo) ---
    status_callback("Analisando logs de rede para URL de VOD...")
    logs = driver.get_log('performance')
    
    found_urls = {
        'm3u8': None,
        'mp4': None,
        'mpd': None,
        'manifest.json': None
    }

    for log in logs:
        try:
            message = json.loads(log['message'])
            url = message.get('message', {}).get('params', {}).get('request', {}).get('url', '')
            if url:
                # Filtrar por domínios que geralmente hospedam conteúdo de vídeo do Weverse
                if any(domain in url for domain in ['weverse', 'cloudfront.net', 'akamai.net', 'cdn.weverse.io']):
                    if '.m3u8' in url:
                        found_urls['m3u8'] = url
                    elif '.mp4' in url:
                        found_urls['mp4'] = url
                    elif '.mpd' in url:
                        found_urls['mpd'] = url
                    elif 'manifest.json' in url:
                        found_urls['manifest.json'] = url
        except (KeyError, json.JSONDecodeError):
            continue

    # Prioridade de retorno: M3U8 (HLS) > MPD (DASH) > MP4 > Manifest (pode ser o próprio MPD/M3U8)
    if found_urls['m3u8']:
        video_url = found_urls['m3u8']
        status_callback(f"URL de VOD (.m3u8) encontrada nos logs: {video_url}")
    elif found_urls['mpd']:
        video_url = found_urls['mpd']
        status_callback(f"URL de VOD (.mpd) encontrada nos logs: {video_url}")
    elif found_urls['mp4']:
        video_url = found_urls['mp4']
        status_callback(f"URL de VOD (.mp4) encontrada nos logs: {video_url}")
    elif found_urls['manifest.json']:
        video_url = found_urls['manifest.json']
        status_callback(f"URL de VOD (manifest.json) encontrada nos logs: {video_url}")

    if video_url:
        print(f"Direct VOD link found: {video_url}")
        return video_url
    else:
        status_callback("Nenhuma URL de VOD direta encontrada pelos métodos conhecidos.")
        print("Could not find direct video URL for VODs using current methods.")
        return None

def download_video(video_url, output_file, status_callback):
    """
    Downloads the video using ffmpeg.
    Provides basic status updates via the status_callback.
    """
    status_callback("Iniciando download do vídeo...")
    print(f"Downloading video from: {video_url}")
    
    command = f'ffmpeg -i "{video_url}" -c copy "{output_file}" -stats -loglevel warning -hide_banner -y'
    
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        if process.stdout is None:
            raise RuntimeError("Falha ao obter stdout do processo ffmpeg.")

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', output)
                if match:
                    current_time = match.group(1)
                    status_callback(f"Baixando: {current_time}...")
                print(output.strip()) 
        
        rc = process.poll()
        if rc != 0:
            raise subprocess.CalledProcessError(rc if rc is not None else -1, command, output=output)

        status_callback(f"Download concluído. Arquivo salvo como {os.path.basename(output_file)}")
        print(f"Download completed. File saved as {output_file}")

    except subprocess.CalledProcessError as e:
        error_msg = f"Erro no download com ffmpeg. Verifique se o ffmpeg está no PATH e se o URL é válido. Erro: {e.output}"
        status_callback(f"Erro no download: {error_msg}")
        print(error_msg)
        messagebox.showerror("Erro no FFMPEG", error_msg)
        raise 
    except Exception as e:
        error_msg = f"Um erro inesperado ocorreu durante o download: {e}"
        status_callback(f"Erro no download: {error_msg}")
        print(error_msg)
        messagebox.showerror("Erro Inesperado", error_msg)
        raise

def main(video_page_url, output_file, status_callback):
    """
    Main function to orchestrate the video extraction and download for VODs.
    """
    status_callback("Iniciando processo de download do VOD...")
    
    chrome_options = Options()
    chrome_options.add_argument('--log-level=3') 
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    driver = None 
    try:
        status_callback("Instalando/verificando ChromeDriver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # NOVO: Solicita ao usuário o arquivo de cookies
        from tkinter import filedialog
        cookie_path = filedialog.askopenfilename(
            title="Selecione o arquivo de cookies do Weverse",
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")]
        )
        if not cookie_path:
            status_callback("Operação cancelada: Nenhum arquivo de cookies selecionado.")
            messagebox.showerror("Cookies necessários", "Operação cancelada: Nenhum arquivo de cookies selecionado.")
            return
        # Carrega cookies do arquivo selecionado
        def load_cookies_from_path(driver, status_callback, path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                driver.get("https://weverse.io/home")
                time.sleep(2)
                for cookie in cookies:
                    if 'expiry' in cookie and (isinstance(cookie['expiry'], float) or cookie['expiry'] is None):
                        if cookie['expiry'] is None:
                            del cookie['expiry']
                        else:
                            cookie['expiry'] = int(cookie['expiry'])
                    try:
                        driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"Aviso: Não foi possível adicionar o cookie '{cookie.get('name', 'N/A')}': {e}")
                        continue
                driver.refresh()
                status_callback("Cookies carregados e aplicados.")
                return True
            except Exception as e:
                status_callback(f"Erro ao carregar cookies: {e}")
                messagebox.showerror("Erro de Cookies", f"Erro ao carregar cookies: {e}")
                return False
        if not load_cookies_from_path(driver, status_callback, cookie_path):
            return
        # ...continua fluxo normal...
        status_callback("Navegador iniciado. Carregando página do VOD...")
        driver.get(video_page_url)
        print(f"Loading page: {video_page_url}")
        
        try:
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            WebDriverWait(driver, 30).until(
                EC.any_of( 
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'video')),
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[src*="weverse"], iframe[src*="vimeo"], iframe[src*="youtube"]')) 
                )
            )
            status_callback("Player de VOD potencialmente carregado. Aguardando conteúdo...")
            time.sleep(5) 
        except TimeoutException:
            status_callback("Tempo esgotado para carregar o player de vídeo. Tentando extração de qualquer forma.")
            print("Timeout waiting for video player elements.")
        except Exception as e:
            status_callback(f"Erro ao esperar pelo player: {e}")
            print(f"Error waiting for video player: {e}")
        
        title = driver.title.strip()
        if not title or "Weverse" in title: 
            title = "Weverse_VOD_" + str(int(time.time()))
        
        if not output_file.lower().endswith('.mp4'):
            output_file += '.mp4'
        
        video_url = extract_video_url_for_vods(driver, status_callback) 

        if video_url:
            print(f"Direct VOD link found: {video_url}")
            download_video(video_url, output_file, status_callback)
            status_callback("Download do VOD concluído com sucesso!")
            messagebox.showinfo("Sucesso", f"Vídeo salvo como: {os.path.basename(output_file)}")
        else:
            status_callback("Não foi possível encontrar a URL direta do VOD. Verifique o console para mais detalhes.")
            print("Could not find direct video URL for VOD.")
            messagebox.showerror("Erro", "Não foi possível encontrar a URL direta do VOD. A estrutura da página pode ter mudado ou o vídeo usa um método de streaming não suportado.")
    
    except WebDriverException as e:
        error_message = f"Não foi possível iniciar ou controlar o navegador. Verifique sua versão do Chrome/ChromeDriver, conexão com a internet ou permissões. Erro: {e}"
        status_callback(f"Erro fatal: {error_message}")
        messagebox.showerror("Erro de Navegador", error_message)
        print(error_message)
    except Exception as e:
        error_message = f"Ocorreu um erro geral no processo: {e}"
        status_callback(f"Erro fatal: {error_message}")
        messagebox.showerror("Erro Crítico", error_message)
        print(error_message)
    finally:
        if driver:
            driver.quit()
            print("Navegador fechado.")

# --- Funções da Interface Gráfica (Tkinter) ---

def update_status_label(message):
    """Updates the status label in the GUI. Ensures thread safety."""
    root.after(0, lambda: status_label.config(text=message))

def get_title_from_url_helper(url, status_callback):
    """
    Helper function to fetch the page title in a headless browser.
    """
    try:
        status_callback("Buscando título da página...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--log-level=3')
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        title = driver.title.strip()
        driver.quit()
        
        if not title or "Weverse" in title: 
            return f"Weverse_VOD_{int(time.time())}"
        
        clean_title = re.sub(r'[\\/:*?"<>|]', '', title)
        return clean_title
    except WebDriverException as e:
        print(f"Erro ao obter título (WebDriver): {e}")
        status_callback("Erro ao buscar título. Usando nome padrão.")
        return f"Weverse_VOD_{int(time.time())}"
    except Exception as e:
        print(f"Erro genérico ao obter título: {e}")
        status_callback("Erro ao buscar título. Usando nome padrão.")
        return f"Weverse_VOD_{int(time.time())}"

def start_download_thread():
    """
    Handles the start download button click, validates input,
    and starts the download process in a separate thread.
    """
    video_page_url = url_entry.get().strip()

    if not video_page_url:
        messagebox.showerror("Erro", "Por favor, insira a URL do vídeo.")
        return
    
    if "weverse.io" not in video_page_url and "weverse.com" not in video_page_url:
        if not messagebox.askyesno("Aviso de URL", "Esta URL pode não ser uma URL válida do Weverse. Deseja continuar mesmo assim?"):
            return

    vod_title = get_title_from_url_helper(video_page_url, update_status_label)
    
    output_path = filedialog.asksaveasfilename(
        defaultextension=".mp4",
        filetypes=[("Arquivos MP4", "*.mp4"), ("Todos os Arquivos", "*.*")],
        title="Salvar vídeo como...",
        initialfile=vod_title + ".mp4"
    )
    
    if not output_path: 
        update_status_label("Download cancelado pelo usuário.")
        return

    update_status_label("Iniciando processo de download do VOD...")
    threading.Thread(target=main, args=(video_page_url, output_path, update_status_label), daemon=True).start()

# --- Configuração da GUI ---
root = tk.Tk()
root.title("Weverse VOD Downloader")
root.geometry("550x450") # Aumenta a altura da janela
root.resizable(False, False)
root.config(bg="#f0f0f0")

frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=20)
frame.pack(pady=10, fill=tk.BOTH, expand=True) # Reduz o pady superior para mais espaço

title_label = tk.Label(frame, text="Weverse VOD Downloader", font=("Helvetica", 18, "bold"), fg="#333", bg="#f0f0f0")
title_label.grid(row=0, column=0, columnspan=2, pady=10) # Reduz o pady para o título

url_label = tk.Label(frame, text="URL do VOD:", font=("Helvetica", 12), bg="#f0f0f0")
url_label.grid(row=1, column=0, padx=10, pady=5, sticky="w") # Reduz pady

url_entry = tk.Entry(frame, width=45, font=("Helvetica", 12), borderwidth=2, relief="groove")
url_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

frame.grid_columnconfigure(1, weight=1)

# Botão de Download Principal
download_button = tk.Button(frame, text="Baixar VOD", command=start_download_thread,
                            font=("Helvetica", 14, "bold"), bg="#4CAF50", fg="white",
                            relief="raised", bd=3, width=25, cursor="hand2")
download_button.grid(row=2, column=0, columnspan=2, pady=15)

status_label = tk.Label(root, text="Pronto para baixar VODs! Selecione o cookie manualmente ao baixar.", bd=1, relief=tk.SUNKEN, anchor=tk.W, font=("Helvetica", 10), fg="#555")
status_label.pack(side=tk.BOTTOM, fill=tk.X, ipady=5)

root.mainloop()