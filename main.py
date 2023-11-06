from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'secret'
socket = SocketIO(app)

rooms = {}

@socket.on('join')
def join(data):
    if data['room_code'] in rooms:
        room_code = data['room_code']
        rooms[room_code]["members"] += 1
        rooms[room_code]["clients"].append(request.sid)

@socket.on('leave')
def leave(data):
    if data['room_code'] in rooms:
        room_code = data['room_code']
        rooms[room_code]["members"] -= 1
        rooms[room_code]["clients"].remove(request.sid)
        rooms.pop(room_code, None) if rooms[room_code]['members'] == 0 else None

@socket.on('message')
def handle_message(message):
    if message['room_code'] in rooms:
        room_code = message['room_code']
        message = {"username": message['username'], "msg": message['msg']}
        rooms[room_code]["messages"].append(message)
        clients = rooms[room_code]["clients"]
        emit('recieved_msg', message, broadcast=True, to=clients, include_self=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        room_code = request.form.get('room-code')
        join = request.form.get('Join', False)
        create = request.form.get('create', False)
        if name is None or name == '' or room_code is None or room_code == '':
            session['error'] = "All above fields are required"
            return redirect(url_for('index'))

        if room_code in rooms and join != False:
            session['username'] = name
            session['room'] = room_code
            return redirect(url_for('chat'))

        if room_code not in rooms and create != False:
            rooms[room_code] = {"members":0, "messages":[], "clients":[]}
            session['username'] = name
            session['room'] = room_code
            return redirect(url_for('chat'))

        if room_code not in rooms and join != False:
            session['error'] = "Room Not Found"
            return redirect(url_for('index'))

        if room_code in rooms and create != False:
            session['error'] = "Room already exists"
            return redirect(url_for('index'))

    error = session.pop('error', None)
    return render_template('index.html', error=error)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    usernmae = session.get('username', None)
    room = session.get('room', None)
    messages = rooms.get(room, {}).get("messages", [])
    return render_template('chat.html', username=usernmae, messages=messages, room=room)

@app.route('/join_room', methods=['GET', 'POST'])
def join_room():
    room = request.get_json()['room_code']
    username = request.get_json()['username']
    if room in rooms:
        messages = rooms.get(room, {}).get("messages", [])
        return {"status": "success", "messages": messages}, 200
    if room is None or username is None:
        return {"error": "Invalid room code or username"}, 400
    if room not in rooms:
        return {"error": "Invalid room code"}, 400
    return {"error": "Something went wrong"}, 500

@app.route('/create_room', methods=['GET', 'POST'])
def create_room():
    room = request.get_json()['room_code']
    username = request.get_json()['username']
    if room in rooms:
        return {"error": "Room already exists"}, 400
    if room is None or username is None:
        return {"error": "Invalid room code or username"}, 400
    if room not in rooms:
        rooms[room] = {"members":0, "messages":[], "clients":[]}
        return {"status": "success"}, 200
    return {"error": "Something went wrong"}, 500

if __name__ == '__main__':
    socket.run(app, debug=True, host='0.0.0.0', port=5000)
