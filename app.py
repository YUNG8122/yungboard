from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yungboard'
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10e6)

ROOMS = {}

@app.route('/')
def index(): return render_template('index.html')

@socketio.on('join')
def on_join(data):
    room = data.get('room', 'main')
    join_room(room)
    if room not in ROOMS:
        ROOMS[room] = {'lines': [], 'objects': {}, 'camera': {'offX':0, 'offY':0, 'scale':1}}
    
    emit('load_state', {
        'lines': ROOMS[room]['lines'],
        'objects': ROOMS[room]['objects'],
        'camera': ROOMS[room]['camera']
    }, to=request.sid)
    
    if data.get('name'):
        emit('user_joined', data.get('name'), to=room, include_self=False)

@socketio.on('camera_move')
def on_camera_move(data):
    room = data.get('room')
    if room in ROOMS:
        ROOMS[room]['camera'] = {'offX': data['offX'], 'offY': data['offY'], 'scale': data['scale']}
    emit('camera_move', data, to=room, include_self=False)

@socketio.on('cursor_move')
def on_cursor_move(data):
    data['sender'] = request.sid
    emit('cursor_move', data, to=data['room'], include_self=False)

@socketio.on('laser')
def on_laser(data):
    data['sender'] = request.sid
    emit('laser', data, to=data['room'], include_self=False)

@socketio.on('draw')
def on_draw(data):
    if data['room'] in ROOMS: ROOMS[data['room']]['lines'].append(data)
    emit('draw', data, to=data['room'], include_self=False)

@socketio.on('line_delete')
def on_line_delete(data):
    if data['room'] in ROOMS: 
        ROOMS[data['room']]['lines'] = [l for l in ROOMS[data['room']]['lines'] if l.get('id') != data['id']]
    emit('line_delete', data['id'], to=data['room'], include_self=False)

@socketio.on('object_create')
def on_obj_create(data):
    if data['room'] in ROOMS: ROOMS[data['room']]['objects'][data['id']] = data
    emit('object_create', data, to=data['room'], include_self=False)

@socketio.on('object_update')
def on_obj_update(data):
    if data['room'] in ROOMS and data['id'] in ROOMS[data['room']]['objects']:
        ROOMS[data['room']]['objects'][data['id']].update({k: v for k, v in data.items() if k not in ['id', 'room']})
    emit('object_update', data, to=data['room'], include_self=False)

@socketio.on('object_edit')
def on_obj_edit(data):
    if data['room'] in ROOMS and data['id'] in ROOMS[data['room']]['objects']:
        ROOMS[data['room']]['objects'][data['id']]['content'] = data['content']
    emit('object_edit', data, to=data['room'], include_self=False)

@socketio.on('object_delete')
def on_obj_delete(data):
    if data['room'] in ROOMS and data['id'] in ROOMS[data['room']]['objects']: 
        del ROOMS[data['room']]['objects'][data['id']]
    emit('object_delete', data['id'], to=data['room'], include_self=False)

@socketio.on('clear_all')
def on_clear_all(data):
    if data['room'] in ROOMS: ROOMS[data['room']] = {'lines': [], 'objects': {}, 'camera': ROOMS[data['room']]['camera']}
    emit('clear_all', {}, to=data['room'], include_self=False)

@socketio.on('load_project')
def on_load_project(data):
    if data['room'] in ROOMS:
        ROOMS[data['room']]['lines'] = data.get('lines', [])
        ROOMS[data['room']]['objects'] = {o['id']: o for o in data.get('objects', [])}
        emit('load_state', {'lines': ROOMS[data['room']]['lines'], 'objects': ROOMS[data['room']]['objects'], 'camera': ROOMS[data['room']]['camera']}, to=data['room'])

@socketio.on('disconnect')
def on_disconnect(): emit('user_left', request.sid, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
