import requests

PORT=8000
resp = requests.post(
    f"http://localhost:{PORT}/login",
    data={"username": "alice", "password":"alice"}
)
print(resp.status_code)
print(resp.json())

token = resp.json()["token"]
resp = requests.get(
    f"http://localhost:{PORT}/demo/api/v1/example/endpoint",
    headers={"Authorization": f"Bearer {token}"}
)
print(resp.status_code)
print(resp.json())
print(resp.headers)


resp = requests.get(
    f"http://localhost:{PORT}/demo/api/v1/example/endpoint2",
    headers={"Authorization": f"Bearer {token}"}
)
print(resp.status_code)
print(resp.json())
print(resp.headers)

resp = requests.post(
    f"http://localhost:{PORT}/demo/api/v1/example/endpoint2",
    headers={"Authorization": f"Bearer {token}"}
)
print(resp.status_code)
print(resp.json())
print(resp.headers)


resp = requests.get(
    f"http://localhost:{PORT}/demo/api/v1/example/endpoint3/specific",
    headers={"Authorization": f"Bearer {token}"}
)
print(resp.status_code)
print(resp.json())
print(resp.headers)

resp = requests.get(
    f"http://localhost:{PORT}/demo/api/v1/example/endpoint3/else",
    # headers={"Authorization": f"Bearer {token}"}
)
print(resp.status_code)
print(resp.json())
print(resp.headers)