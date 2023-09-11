import os
import requests
from flask import Flask, request, jsonify
import sqlite3
import json

app = Flask(__name__)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('registration.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            nrc_number TEXT,
            num_children INTEGER,
            health_center TEXT,
            password TEXT,
            pin TEXT,
            children_info TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Function to insert registration data into the database
def insert_registration(user_id, name, nrc_number, num_children, health_center, password, pin):
    conn = sqlite3.connect('registration.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO registrations (user_id, name, nrc_number, num_children, health_center, password, pin)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, nrc_number, num_children, health_center, password, pin))
    conn.commit()
    conn.close()

# Function to check if a user is already registered
def is_user_registered(user_id):
    conn = sqlite3.connect('registration.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM registrations WHERE user_id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

ussd_menu = {
    "1": "Welcome to USSD App. Press 1 to Register, 2 for Help, or 0 to exit.",
    "2": "Welcome back! Press 1 for Profile, 2 for Pin Menu, or 3 for Help.",
    "1*1": "You selected Register. Choose a sub-action:\n1. Name\n2. NRC Number\n3. Number Of Children\n4. Health Centre Registered Under\n5. Set Password\n0. Go back",
    "1*1*1": "You selected Name. Enter your name or 0 to go back.",
    "1*1*2": "You selected NRC Number. Enter your NRC Number or 0 to go back.",
    "1*1*3": "You selected Number Of Children. Enter the number of children or 0 to go back.",
    "1*1*4": "You selected Health Centre Registered Under. Enter the health centre name or 0 to go back.",
    "1*1*5": "You selected Set Password. Enter your desired password or 0 to go back.",
    "1*1*1*1": "Name confirmed!",
    "1*1*2*1": "NRC Number confirmed!",
    "1*1*3*1": "Number Of Children confirmed!",
    "1*1*4*1": "Health Centre Registered Under confirmed!",
    "1*1*5*1": "Password set successfully!",
    "2*1": "You selected Profile. Here's your profile information:\nName: {name}\nNRC Number: {nrc}\nNumber Of Children: {num_children}\nHealth Centre Registered Under: {health_center}\n1. Edit Profile\n0. Go back",
    "2*1*1": "You selected Edit Profile. Choose a sub-action:\n1. Name\n2. NRC Number\n3. Number Of Children\n4. Health Centre Registered Under\n5. Change Password\n0. Go back",
    "2*1*1*1": "You selected Name. Enter your new name or 0 to go back.",
    "2*1*1*2": "You selected NRC Number. Enter your new NRC Number or 0 to go back.",
    "2*1*1*3": "You selected Number Of Children. Enter the new number of children or 0 to go back.",
    "2*1*1*4": "You selected Health Centre Registered Under. Enter your new health centre name or 0 to go back.",
    "2*1*1*5": "You selected Change Password. Enter your new password or 0 to go back.",
    "2*2": "You selected Pin Menu. Choose an option:\n1. Enter Pin\n2. Reset Pin\n3. Help\n0. Go back",
    "2*2*1": "You selected Enter Pin. Enter your PIN or 0 to go back.",
    "2*2*1*1": "You entered your PIN successfully! Choose an option:\n1. Register Child\n2. View Existing Children\n0. Go back",
    "2*2*1*1*1": "You selected Register Child. Enter the child's name or 0 to go back.",
    "2*2*1*1*1*1": "Enter the child's gender (e.g., Male, Female) or 0 to go back.",
    "2*2*1*1*1*1*1": "Enter the date the child was first seen at the clinic (YYYY-MM-DD) or 0 to go back.",
    "2*2*1*1*1*1*1*1": "Enter the child's date of birth (YYYY-MM-DD) or 0 to go back.",
    "2*2*1*1*1*1*1*1*1": "Enter the child's birth weight (e.g., 3.2 kg) or 0 to go back.",
    "2*2*1*1*1*1*1*1*1*1": "Enter the place of birth or 0 to go back.",
    "2*2*1*1*1*1*1*1*1*1*1": "Child's Particulars saved successfully!",
    "2*2*1*1*2": "You selected View Existing Children. Choose a child to view or 0 to go back.",
    "2*2*1*1*2*0": "No child registered. Press 0 to go back and register a child.",
}

# Function to save child particulars in JSON format in the database
def save_child_particulars(user_id, child_info):
    conn = sqlite3.connect('registration.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE registrations SET children_info = ? WHERE user_id = ?', (child_info, user_id))
    conn.commit()
    conn.close()

# Function to retrieve existing children information
def retrieve_existing_children(user_id):
    conn = sqlite3.connect('registration.db')
    cursor = conn.cursor()
    cursor.execute('SELECT children_info FROM registrations WHERE user_id = ?', (user_id,))
    children_info = cursor.fetchone()[0]
    conn.close()
    return children_info

# Function to retrieve child information by index
def retrieve_child_info(user_id, child_index):
    children_info = retrieve_existing_children(user_id)
    if children_info:
        children = json.loads(children_info)
        if 0 <= child_index < len(children):
            return children[child_index]
    return None

# Handling USSD callback from Africa's Talking
@app.route('/ussd-callback', methods=['POST'])
def ussd_callback():
    # Parse the incoming USSD session data from Africa's Talking
    session_id = request.json['sessionId']
    phone_number = request.json['phoneNumber']
    user_input = request.json['text']

    # Check if the user is already registered
    if is_user_registered(session_id):
        if user_input == "":
            response_text = ussd_menu.get("2")
        else:
            response_text = process_ussd_input(session_id, user_input, is_registered=True)
    else:
        if user_input == "":
            response_text = ussd_menu.get("1")
        else:
            response_text = process_ussd_input(session_id, user_input, is_registered=False)

    response = {
        "sessionId": session_id,
        "phoneNumber": phone_number,
        "text": response_text,
        "type": "response"
    }

    # Send the response back to Africa's Talking's USSD API
    send_ussd_response(response)

    return jsonify(response)

# Function to send the USSD response to Africa's Talking's USSD API
def send_ussd_response(response):
    username = 'Neville Nyati'  # Replace with your Africa's Talking username
    api_key = 'dee9d2a1f7961cef99c9d30b8354cb056ba244d8a37835072f23b2350d2ae227'    # Replace with your Africa's Talking API key
    url = 'https://api.africastalking.com/ussd/send'

    headers = {
        'Content-Type': 'application/json',
        'apiKey': api_key,
    }

    try:
        response = requests.post(url, json=response, headers=headers)
        if response.status_code == 201:
            print("USSD response sent successfully")
        else:
            print("Failed to send USSD response")
    except Exception as e:
        print(f"Error sending USSD response: {str(e)}")

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
