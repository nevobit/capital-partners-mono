import requests

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def get_accounts(self):
        response = self.session.get(f"{self.base_url}/accounts")
        response.raise_for_status()
        return response.json()

    def get_bots(self):
        response = self.session.get(f"{self.base_url}/bots")
        response.raise_for_status()
        return response.json()

    def update_bot_status(self, bot_id: str, status: bool):
        response = self.session.patch(f"{self.base_url}/bots/{bot_id}", json={"active": status})
        response.raise_for_status()
        return response.json()