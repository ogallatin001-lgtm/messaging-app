import os
import uuid
from datetime import datetime

from flask import (
    Flask,
    request,
    jsonify,
    session,
    send_from_directory,
    abort,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_PATH = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_PATH, exist_ok=True)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')

# allow cross-origin for testing (remove or lock down in production)
@app.after_request

def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp


db = SQLAlchemy(app)

# ------ models ------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    friends = db.relationship('Friend', back_populates='user', cascade='all, delete')
    rooms = db.relationship('RoomMember', back_populates='user', cascade='all, delete')


class Room(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(120))
    type = db.Column(db.String(16))  # 'room' or 'dm'
    members = db.relationship('RoomMember', back_populates='room', cascade='all, delete')
    messages = db.relationship('Message', back_populates='room', cascade='all, delete')


class RoomMember(db.Model):
    room_id = db.Column(db.String(64), db.ForeignKey('room.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    room = db.relationship('Room', back_populates='members')
    user = db.relationship('User', back_populates='rooms')


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(64), db.ForeignKey('room.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text)
    file_path = db.Column(db.String(256))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    room = db.relationship('Room', back_populates='messages')


class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='friends', foreign_keys=[user_id])


# ------ helpers ------

def get_current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return User.query.get(uid)


def require_auth():
    user = get_current_user()
    if not user:
        abort(401)
    return user


# ------ auth endpoints ------

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not email or not password:
        return jsonify({'error': 'email and password required'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'already exists'}), 400
    u = User(email=email, password_hash=generate_password_hash(password))
    db.session.add(u)
    db.session.commit()
    session['user_id'] = u.id
    return jsonify({'email': u.email})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    u = User.query.filter_by(email=email).first()
    if not u or not check_password_hash(u.password_hash, password):
        return jsonify({'error': 'invalid credentials'}), 401
    session['user_id'] = u.id
    return jsonify({'email': u.email})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})


# ------ utility endpoints ------

@app.route('/api/user')
def whoami():
    user = get_current_user()
    if not user:
        return jsonify({'user': None})
    # gather room ids and friend emails
    rooms = [rm.room_id for rm in user.rooms]
    friends = [User.query.get(f.friend_id).email for f in user.friends]
    return jsonify({'user': {'email': user.email, 'rooms': rooms, 'friends': friends}})


@app.route('/api/rooms', methods=['GET'])
def list_rooms():
    user = require_auth()
    return jsonify([{'id': rm.room_id, 'name': rm.room.name} for rm in user.rooms])


@app.route('/api/rooms', methods=['POST'])
def create_room():
    user = require_auth()
    data = request.json or {}
    name = data.get('name')
    rid = uuid.uuid4().hex
    r = Room(id=rid, name=name, type='room')
    r.members.append(RoomMember(user=user))
    db.session.add(r)
    db.session.commit()
    return jsonify({'id': rid, 'name': name})


@app.route('/api/rooms/join', methods=['POST'])
def join_room():
    user = require_auth()
    data = request.json or {}
    rid = data.get('roomId')
    r = Room.query.get(rid)
    if not r:
        return jsonify({'error': 'not found'}), 404
    if not any(m.user_id == user.id for m in r.members):
        r.members.append(RoomMember(user=user))
        db.session.commit()
    return jsonify({'id': r.id, 'name': r.name})


@app.route('/api/friends', methods=['GET'])
def list_friends():
    user = require_auth()
    return jsonify([User.query.get(f.friend_id).email for f in user.friends])


@app.route('/api/friends', methods=['POST'])
def add_friend():
    user = require_auth()
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    other = User.query.filter_by(email=email).first()
    if not other:
        return jsonify({'error': 'user not found'}), 404
    if other.id == user.id:
        return jsonify({'error': 'cannot add self'}), 400
    # add each way if not exists
    if not any(f.friend_id == other.id for f in user.friends):
        user.friends.append(Friend(friend_id=other.id))
    if not any(f.friend_id == user.id for f in other.friends):
        other.friends.append(Friend(friend_id=user.id))
    # ensure dm room exists
    ids = sorted([user.id, other.id])
    dm_id = f"dm_{ids[0]}_{ids[1]}"
    dm = Room.query.get(dm_id)
    if not dm:
        dm = Room(id=dm_id, name='Direct message', type='dm')
        dm.members.append(RoomMember(user=user))
        dm.members.append(RoomMember(user=other))
        db.session.add(dm)
    db.session.commit()
    return jsonify({'friend': email})


@app.route('/api/rooms/<room_id>/messages', methods=['GET'])
def get_messages(room_id):
    user = require_auth()
    r = Room.query.get(room_id)
    if not r or not any(m.user_id == user.id for m in r.members):
        return jsonify({'error': 'not allowed'}), 403
    msgs = []
    for m in r.messages:
        msgs.append({
            'sender': User.query.get(m.sender_id).email,
            'text': m.text,
            'fileUrl': f"/uploads/{os.path.basename(m.file_path)}" if m.file_path else None,
            'fileName': os.path.basename(m.file_path) if m.file_path else None,
            'timestamp': m.timestamp.isoformat()
        })
    return jsonify(msgs)


@app.route('/api/rooms/<room_id>/messages', methods=['POST'])
def post_message(room_id):
    user = require_auth()
    r = Room.query.get(room_id)
    if not r or not any(m.user_id == user.id for m in r.members):
        return jsonify({'error': 'not allowed'}), 403
    text = request.form.get('text')
    file = request.files.get('file')
    file_path = None
    if file:
        filename = secure_filename(file.filename)
        fname = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(UPLOAD_PATH, fname)
        file.save(file_path)
    msg = Message(room=r, sender_id=user.id, text=text or None, file_path=file_path)
    db.session.add(msg)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/uploads/<path:name>')
def serve_upload(name):
    return send_from_directory(UPLOAD_PATH, name)


# run helper
if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
