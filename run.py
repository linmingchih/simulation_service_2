from app import create_app
from waitress import serve
import socket
import threading
import webbrowser
import time

app = create_app()

def open_browser(url):
    # 等待幾秒讓 server 啟動
    time.sleep(1)
    webbrowser.open(url)

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = host

    url = f"http://127.0.0.1:{port}"

    # 啟動新執行緒開啟瀏覽器
    threading.Thread(target=open_browser, args=(url,)).start()

    print(f"Server running on http://{ip}:{port}")
    serve(app, host=host, port=port)
