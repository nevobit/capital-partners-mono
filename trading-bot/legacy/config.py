import json
import os

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"No se encontró el archivo de configuración en la ruta: {config_path}")

if __name__ == "__main__":
    try:
        config = load_config()
        print("Configuración cargada correctamente")
    except FileNotFoundError as e:
        print(e)
