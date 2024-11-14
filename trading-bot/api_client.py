import requests
import hmac
import hashlib
import json
import time
from typing import Dict, Any

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.api_secret = "b17b7d9f8a9c1f4e5d8e3a9b2c7f6e3d1a2b9c7e5d8f1b2c3a4e7f6b9d2e3c1f7a5b6d"

    def generate_signature(self, url: str, body: str, timestamp: int) -> str:
        data_to_sign = f"{url}|{body}|{timestamp}"
        return hmac.new(self.api_secret.encode(), data_to_sign.encode(), hashlib.sha256).hexdigest()

    def prepare_headers(self, full_url: str, body: Dict[str, Any]) -> Dict[str, str]:
        timestamp = str(int(time.time() * 1000))  # Timestamp en segundos, como string
        body_string = json.dumps(body) if body else "{}"
        signature = self.generate_signature(full_url, body_string, timestamp)
        headers = {
            'Content-Type': 'application/json',
            'X-Timestamp': timestamp,
            'X-Signature': signature,
            'X-path': full_url
        }
        return headers

    def make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        full_url = f"{self.base_url}{endpoint}"
        headers = self.prepare_headers(full_url, data or {})
        try:
            response = self.session.request(method, full_url, headers=headers, json=data)
            
            response.raise_for_status()
            if response.text:
                return response.json()
            else:
                return {}
            
        except requests.exceptions.RequestException as e:
            print(e)
            if e.response:
                print(f"Response error: {e.response.status_code}, {e.response.text}")
            elif e.request:
                print(f"Network error: {e.request}")
            else:
                print(f"Error: {str(e)}")
            raise

    def get_accounts(self) -> Dict[str, Any]:
        return self.make_request('GET', '/accounts')

    def get_bots(self) -> Dict[str, Any]:
        return self.make_request('GET', '/bots')

    def update_bot_status(self, bot_id: str, status: bool) -> Dict[str, Any]:
        return self.make_request('PATCH', f"/bots/{bot_id}", {'active': status})

    def create_operation(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.make_request('POST', '/operations', operation_data)
    
    def update_operation(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.make_request('PATCH', "/operations", operation_data)
