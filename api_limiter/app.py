from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

# Dummy user data for demonstration purposes
users = {
    "user1": "password1",
    "user2": "password2"
}

# Function to check if a username and password are valid
def authenticate(username, password):
    return username in users and users[username] == password

# Custom decorator for authenticating API endpoints
def requires_authentication(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        auth = request.authorization
        print(auth)
        if not auth or not authenticate(auth.username, auth.password):
            return auth, 401
        return func(*args, **kwargs)
    return decorated

@app.route("/public")
def public_endpoint():
    return "Public endpoint"

@app.route("/private")
@requires_authentication
def private_endpoint():
    return "Private endpoint"

if __name__ == "__main__":
    app.run()
