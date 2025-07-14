from app import create_app
from waitress import serve
import socket

app = create_app()

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = host
    # Display the address where the app will be served
    print(f"Server running on http://{ip}:{port}")
    # Use waitress for production-ready serving
    serve(app, host=host, port=port)
