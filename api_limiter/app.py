from datetime import datetime, timedelta
from flask import Flask,request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)

# Dictionary to keep track of penalties for each IP address
penalties = {}
penalty_lock = threading.Lock()

# Time when penalty ends for all users
penalty_end_time = datetime.now()
penalty_end_time_lock = threading.Lock()

SERVER_START_TIME = timedelta(seconds = datetime.now().second)
PENALTY_IN_SECONDS = 60 
MAX_API_CALLS_ALLOWED = 3
TOO_MANY_REQUESTS = 429

def calculate_seconds_left_in_current_minute_after_last_api_call():
    
    current_time = datetime.now()
    time_left = 0
    
    if timedelta(seconds=current_time.second) > SERVER_START_TIME:
        time_left = timedelta(seconds=current_time.second) - SERVER_START_TIME
    else:
        time_left = timedelta(seconds=60) - SERVER_START_TIME + timedelta(seconds = current_time.second)

    return time_left    


def update_penalty_end_time(new_penalty_end_time):
    with penalty_end_time_lock:
        global penalty_end_time
        penalty_end_time = new_penalty_end_time

# Avoid race conditions when modifying penalties dictionary
def update_penalties(ip_address, penalty_time):
    with penalty_lock:
        penalties[ip_address] = penalty_time


# data endpoint/API ratelimited to MAX_API_CALLS_ALLOWED per user
@app.route("/data")
@limiter.limit("{}/minute".format(MAX_API_CALLS_ALLOWED))  # Limiter function to limit max API calls 
def data():

    # Get the IP address of the requester
    ip_address = get_remote_address()
    
    # Check if the IP address is under penalty
    if ip_address in penalties and penalties[ip_address] > datetime.now():
        return "You are under penalty. You can check remaining time localhost:5000/data/penalty"
    
    return "Welcome to my API"


# API to check remaining penalty time to again access data API
@app.route("/data/penalty")
def data_penalty_end_time():
    ip_address = get_remote_address()

    # Display remaining penalty time if active
    if ip_address in penalties and penalties[ip_address] > datetime.now():
        return "Time remaining: {}".format(penalties[ip_address] - datetime.now())[:-7]

    return "No penalty active"


# home endpoint/API ratelimited to MAX_API_CALLS_ALLOWED
@app.route("/home")
@limiter.limit("{}/minute".format(MAX_API_CALLS_ALLOWED))
def home():
    
    current_time = datetime.now()

    # Checking if penalty is active
    if penalty_end_time > current_time:
        return "You are under penalty. You can check remaining time localhost:5000/home/penalty"
    
    return "Welcome to my API"


# API to check remaining penalty time to again access home API
@app.route("/home/penalty")
def home_penalty_end_time():
    global penalty_end_time

    current_time = datetime.now()

    # Display remaining time if penalty is active
    if penalty_end_time > current_time:
        return "Time remaining: {}".format(penalty_end_time - datetime.now())[:-7]
    
    return "No penalty active"


# Error handling and penalising user when MAX_API_CALLS_ALLOWED threshold is crossed
@app.errorhandler(TOO_MANY_REQUESTS)
def ratelimit_exception_handler(e):
    ip_address2 = request.remote_addr
    ip_address = get_remote_address()
    endpoint = request.endpoint
    current_time = datetime.now()
    error_message = (f"You have exceeded your rate-limit of {MAX_API_CALLS_ALLOWED} calls per minute. You can check penalty time localhost:5000/{endpoint}/penalty  YOur IP address {ip_address}  or {ip_address2}")
    
    # Penalising user based on their IP address
    if endpoint == 'data':
        
        

        if ip_address in penalties and penalties[ip_address] > current_time:
            return error_message

        time_left = calculate_seconds_left_in_current_minute_after_last_api_call()

        # Set the penalty end time
        penalty_time = current_time + (2 * timedelta(seconds=PENALTY_IN_SECONDS)) - time_left
        update_penalties(ip_address, penalty_time)

        return error_message

    # Penalize users after MAX_API_CALLS_ALLOWED exceeded
    elif endpoint == 'home':
        global penalty_end_time

        if penalty_end_time > current_time:
            return error_message


        time_left = calculate_seconds_left_in_current_minute_after_last_api_call()
        
        # Set the penalty end time
        penalty_time = current_time + (2 * timedelta(seconds=PENALTY_IN_SECONDS)) - time_left
        update_penalty_end_time(penalty_time)

        return error_message

    else:
        return "Too many requests"    


if __name__ == "__main__":
    # Run the Flask app
    app.run()
