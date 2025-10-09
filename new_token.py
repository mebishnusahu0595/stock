import requests

url = "https://auth.truedata.in/token"

payload = {
    "username": "tdwsp690",
    "password": "bishnu@690",
    "grant_type": "password"
}
headers = {
    "accept": "application/json",
    "content-type": "application/x-www-form-urlencoded"
}

# Use requests' data encoding for form data
response = requests.post(url, data=payload, headers=headers)

print(response.text)