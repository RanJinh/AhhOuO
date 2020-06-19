import requests
url = "http://127.0.0.1:8001/register_with"
data = '{"node_address": "http://127.0.0.1:8000"}'
res = requests.post(url=url, data=data)
print(res.text)
url = "http://127.0.0.1:8002/register_with"
data = '{"node_address": "http://127.0.0.1:8000"}'
res = requests.post(url=url, data=data)
print(res.text)