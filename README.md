# weverse_downloader

Um downloader para transmissões ao vivo do Weverse.

## Descrição

Este projeto é uma ferramenta para baixar vídeos de transmissões ao vivo do Weverse. Ele utiliza o Selenium para automatizar a navegação e captura de logs de rede, e o ffmpeg para baixar e salvar os vídeos localmente.

## Funcionalidades

- **Extração de URL de Vídeo**: Captura os logs de rede e extrai o link direto do vídeo (.m3u8 ou .mp4).
- **Download de Vídeo**: Utiliza o ffmpeg para baixar o vídeo a partir do link extraído.
- **Interface Gráfica**: Fornece uma interface gráfica simples usando Tkinter para facilitar a entrada da URL do vídeo e a seleção do local de salvamento.

## Requisitos

- Python 3.x
- Selenium
- ChromeDriver
- ffmpeg

## Instalação

1. Clone o repositório:
    ```sh
    git clone https://github.com/The-BitLab-Team/weverse_downloader.git
    cd weverse_downloader
    ```

2. Instale as dependências:
    ```sh
    pip install selenium
    ```

3. Certifique-se de que o ChromeDriver está instalado e disponível no PATH.

4. Instale o ffmpeg conforme as instruções do site oficial.

## Uso

1. Execute o script `downloader.py`:
    ```sh
    python downloader.py
    ```

2. Na interface gráfica, insira a URL do vídeo do Weverse e clique em "Baixar Vídeo".

3. Escolha o local para salvar o vídeo e aguarde a conclusão do download.

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e pull requests.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.