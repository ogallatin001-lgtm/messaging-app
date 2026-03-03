// front‑end communicating with Flask backend
// set API_BASE to the location of your server, e.g. "https://myserver.com" or leave '' for same origin
const API_BASE = '';

let currentRoom = null;
let currentUser = null; // email of logged-in user
let roomPoller = null;

// DOM refs
const authContainer = document.getElementById('auth-container');
const appContainer = document.getElementById('app');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('login-btn');
const registerBtn = document.getElementById('register-btn');
const logoutBtn = document.getElementById('logout-btn');
const actionSelect = document.getElementById('action-select');
const roomsList = document.getElementById('rooms');
const friendsList = document.getElementById('friends');
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const fileInput = document.getElementById('file-input');
const sendBtn = document.getElementById('send-btn');

// --- authentication ---
registerBtn.addEventListener('click', async () => {
    const email = emailInput.value.trim().toLowerCase();
    const password = passwordInput.value;
    if (!email || !password) return alert('Email and password required');
    const res = await fetch(API_BASE + '/api/register', {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password})
    });
    if (!res.ok) return alert((await res.json()).error || 'register failed');
    loginUser(email);
});

loginBtn.addEventListener('click', async () => {
    const email = emailInput.value.trim().toLowerCase();
    const password = passwordInput.value;
    if (!email || !password) return alert('Email and password required');
    const res = await fetch(API_BASE + '/api/login', {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password})
    });
    if (!res.ok) return alert((await res.json()).error || 'login failed');
    loginUser(email);
});

logoutBtn.addEventListener('click', async () => {
    await fetch(API_BASE + '/api/logout', {method: 'POST', credentials: 'include'});
    currentUser = null;
    currentRoom = null;
    if (roomPoller) clearInterval(roomPoller);
    showAuth();
});

// --- main UI actions ---
actionSelect.addEventListener('change', e => {
    const val = e.target.value;
    e.target.value = '';
    switch (val) {
        case 'create-room': createRoom(); break;
        case 'join-room': joinRoom(); break;
        case 'add-user': addUser(); break;
    }
});

sendBtn.addEventListener('click', sendMessage);

function showAuth() {
    authContainer.classList.remove('hidden');
    appContainer.classList.add('hidden');
}

function showApp() {
    authContainer.classList.add('hidden');
    appContainer.classList.remove('hidden');
}

function loginUser(email) {
    currentUser = email;
    showApp();
    refreshUserInfo();
}

// fetch user profile (rooms & friends)
async function refreshUserInfo() {
    const res = await fetch(API_BASE + '/api/user', {credentials: 'include'});
    const json = await res.json();
    if (!json.user) {
        showAuth();
        return;
    }
    currentUser = json.user.email;
    // ask server for all rooms so we can pick up names as well as ids
    const roomsRes = await fetch(API_BASE + '/api/rooms', {credentials: 'include'});
    const allRooms = roomsRes.ok ? await roomsRes.json() : [];
    const mine = allRooms.filter(r => json.user.rooms.includes(r.id));
    populateRooms(mine);
    populateFriends(json.user.friends);
}

function clearLists() {
    roomsList.innerHTML = '';
    friendsList.innerHTML = '';
}

function populateRooms(rooms) {
    clearLists();
    rooms.forEach(r => {
        const li = document.createElement('li');
        li.textContent = r.name || r.id;
        li.addEventListener('click', () => openRoom(r.id));
        roomsList.appendChild(li);
    });
}

function populateFriends(friends) {
    friendsList.innerHTML = '';
    friends.forEach(email => {
        const li = document.createElement('li');
        li.textContent = email;
        li.addEventListener('click', () => addUser(email));
        friendsList.appendChild(li);
    });
}

async function openRoom(rid) {
    currentRoom = rid;
    messagesDiv.innerHTML = '';
    await fetchMessages();
    if (roomPoller) clearInterval(roomPoller);
    roomPoller = setInterval(fetchMessages, 2000);
}

async function fetchMessages() {
    if (!currentRoom) return;
    const res = await fetch(API_BASE + `/api/rooms/${currentRoom}/messages`, {credentials: 'include'});
    if (!res.ok) return;
    const msgs = await res.json();
    messagesDiv.innerHTML = '';
    msgs.forEach(m => renderMessage(m));
}

function renderMessage(m) {
    const div = document.createElement('div');
    div.classList.add('message');
    const senderSpan = document.createElement('span');
    senderSpan.classList.add('sender');
    senderSpan.textContent = m.sender === currentUser ? 'You' : m.sender;
    div.appendChild(senderSpan);
    if (m.text) {
        const textSpan = document.createElement('span');
        textSpan.classList.add('text');
        textSpan.textContent = m.text;
        div.appendChild(textSpan);
    }
    if (m.fileUrl) {
        const a = document.createElement('a');
        a.href = API_BASE + m.fileUrl;
        a.target = '_blank';
        a.textContent = m.fileName || 'file';
        div.appendChild(document.createElement('br'));
        div.appendChild(a);
    }
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendMessage() {
    if (!currentRoom) return alert('No room selected');
    const text = messageInput.value.trim();
    const file = fileInput.files[0];
    const form = new FormData();
    form.append('text', text);
    if (file) form.append('file', file);
    await fetch(API_BASE + `/api/rooms/${currentRoom}/messages`, {
        method: 'POST',
        credentials: 'include',
        body: form
    });
    messageInput.value = '';
    fileInput.value = '';
    fetchMessages();
}

async function createRoom() {
    const name = prompt('Room name');
    if (!name) return;
    await fetch(API_BASE + '/api/rooms', {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    });
    refreshUserInfo();
}

async function joinRoom() {
    const rid = prompt('Room ID to join');
    if (!rid) return;
    await fetch(API_BASE + '/api/rooms/join', {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({roomId: rid})
    });
    refreshUserInfo();
}

async function addUser(providedEmail) {
    const email = providedEmail || prompt('User email to add as friend').trim().toLowerCase();
    if (!email) return;
    const res = await fetch(API_BASE + '/api/friends', {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email})
    });
    if (!res.ok) return alert((await res.json()).error || 'could not add');
    refreshUserInfo();
}

// initial check
(async () => {
    const res = await fetch(API_BASE + '/api/user', {credentials: 'include'});
    const json = await res.json();
    if (json.user) {
        loginUser(json.user.email);
    } else {
        showAuth();
    }
})();
