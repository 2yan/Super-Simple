import  hmac, hashlib, time, base64
from requests.auth import AuthBase
import ryan_tools as rt
import json

    
    
# Create custom authentication for Exchange
class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or b'').decode()
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message.encode(), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode()

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request


def get_auth():
    with open('creds.json', 'r') as f:
        creds = json.load(f)
    
    return CoinbaseExchangeAuth(creds['API_KEY'], creds['API_SECRET'], creds['API_PASS'])



def save_creds(creds):
    with open('creds.json', 'w') as outfile:
        json.dump(creds, outfile)
        
    