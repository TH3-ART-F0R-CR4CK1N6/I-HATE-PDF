import os
import time
import requests
from threading import Thread

def keep_alive():
    """Mantiene la aplicación activa haciendo ping cada 10 minutos"""
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not app_url:
        print("RENDER_EXTERNAL_URL no configurada, keep-alive deshabilitado")
        return
    
    health_url = f"{app_url}/health"
    
    while True:
        try:
            time.sleep(600)  # Esperar 10 minutos
            response = requests.get(health_url, timeout=30)
            print(f"Keep-alive ping: {response.status_code}")
        except Exception as e:
            print(f"Keep-alive error: {e}")

def start_keep_alive():
    """Inicia el thread de keep-alive"""
    thread = Thread(target=keep_alive, daemon=True)
    thread.start()
    print("Keep-alive thread iniciado")
