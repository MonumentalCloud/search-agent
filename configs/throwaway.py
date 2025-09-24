import requests
import re
import json
import base64

serving_id = 15
bearer_token = 'a972ad45b0f845ef9ea29badd5423d20'
genos_url = 'https://genos.genon.ai:3443'

endpoint = f"{genos_url}/api/gateway/rep/serving/{serving_id}"
headers = dict(Authorization=f"Bearer {bearer_token}")

# endpoint의 모델이름을 확인합니다
response = requests.get(endpoint + '/v1/models', headers=headers, timeout=30)
print(response.text)
model = response.json()['data'][0]['id']
print(model)