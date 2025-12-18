const API_URL = 'http://localhost:5000';
let consecutiveFailures = 0;
const FAILURE_THRESHOLD = 3;
let currentSignId = null;

// === 1. SMART CLIENT (Стійкий до збоїв Fetch) ===

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const getBackoffDelay = (attempt, baseDelayMs = 300) => {
    const jitter = Math.floor(Math.random() * 100);
    return (baseDelayMs * (2 ** attempt)) + jitter;
};

async function fetchWithResilience(url, options = {}) {
    const { retries = 3, timeoutMs = 5000, idempotencyKey = null, ...fetchOptions } = options;

    const headers = new Headers(fetchOptions.headers || {});
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    if (!headers.has('X-Request-Id')) headers.set('X-Request-Id', crypto.randomUUID());
    if (idempotencyKey) headers.set('Idempotency-Key', idempotencyKey);

    const token = localStorage.getItem('access_token');
    if (token) headers.append('Authorization', `Bearer ${token}`);

    let attempt = 0;
    while (attempt <= retries) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            console.log(`📡 Запит ${url} (Спроба ${attempt + 1})`);
            const res = await fetch(url, { ...fetchOptions, headers, signal: controller.signal });
            clearTimeout(timeoutId);

            if (res.ok) {
                resetDegradedMode();
                return res;
            }

            // 429 Rate Limit
            if (res.status === 429) {
                const retryAfter = res.headers.get('Retry-After');
                const wait = (retryAfter ? parseInt(retryAfter) : 1) * 1000;
                console.warn(`429. Чекаємо ${wait}мс`);
                await sleep(wait);
                continue;
            }

            // 5xx Server Errors
            if (res.status >= 500 && attempt < retries) {
                const delay = getBackoffDelay(attempt);
                console.warn(`Помилка ${res.status}. Ретрай через ${delay}мс`);
                await sleep(delay);
                attempt++;
                continue;
            }

            if (res.status === 401) logout();

            const errData = await res.json();
            handleDegradedMode();
            return Promise.reject(errData);

        } catch (err) {
            clearTimeout(timeoutId);
            console.error('Помилка:', err.name === 'AbortError' ? 'Timeout' : err);

            if (attempt < retries) {
                await sleep(getBackoffDelay(attempt));
                attempt++;
            } else {
                handleDegradedMode();
                throw err;
            }
        }
    }
}

// === 2. ДОПОМІЖНІ ФУНКЦІЇ ===

async function generateIdempotencyKey(payload) {
    const str = JSON.stringify(payload);
    const hashBuffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
    return Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 16);
}

function handleDegradedMode() {
    consecutiveFailures++;
    if (consecutiveFailures >= FAILURE_THRESHOLD) {
        const banner = document.getElementById('degradedBanner');
        if(banner) banner.style.display = 'block';
    }
}

function resetDegradedMode() {
    consecutiveFailures = 0;
    const banner = document.getElementById('degradedBanner');
    if(banner) banner.style.display = 'none';
}

// === 3. ЛОГІКА ДОДАТКУ ===

async function loadAllSigns() {
    setLoading('loading', true);
    try {
        const res = await fetchWithResilience(`${API_URL}/signs`);
        const data = await res.json();
        displaySigns(data.data);
    } catch (err) {
        const el = document.getElementById('signsList');
        if(el) el.innerHTML = `<p style="color:red">Помилка: ${err.error || err.message}</p>`;
    }
    setLoading('loading', false);
}

// Відображення списку карток
function displaySigns(signs) {
    const c = document.getElementById('signsList');
    if(!c) return;
    c.innerHTML = '';

    if(!signs || signs.length === 0) {
        c.innerHTML = '<p>Знаки не знайдено</p>';
        return;
    }

    signs.forEach(s => {
        const d = document.createElement('div');
        d.className = 'sign-card';
        d.onclick = () => openDetailModal(s.id);
        d.innerHTML = `
            <span class="category">${s.category}</span>
            <h3>${s.name}</h3>
            <p>${s.description ? s.description.substring(0, 60) + '...' : ''}</p>
            <small style="color: #007bff; display: block; margin-top: 5px;">Натисніть для деталей</small>
        `;
        c.appendChild(d);
    });
}

// --- ДЕТАЛІ ЗНАКА (MODAL) ---
async function openDetailModal(id) {
    try {
        const res = await fetchWithResilience(`${API_URL}/signs/id/${id}`);
        const data = await res.json();
        const sign = data.data;

        currentSignId = sign.id;
        document.getElementById('detailName').textContent = sign.name;
        document.getElementById('detailCategory').textContent = sign.category;
        document.getElementById('detailDescription').textContent = sign.description || "Опис відсутній";

        // Перевірка прав адміна для показу кнопок редагування
        const user = JSON.parse(localStorage.getItem('user'));
        const adminControls = document.getElementById('detailAdminControls');
        if (user && user.role === 'admin') {
            adminControls.style.display = 'block';
        } else {
            adminControls.style.display = 'none';
        }

        document.getElementById('detailModal').style.display = 'flex';
    } catch (e) {
        alert('Не вдалося завантажити деталі');
    }
}

// --- АДМІН ПАНЕЛЬ: ФОРМИ ---

function openSignForm(signToEdit = null) {
    const modal = document.getElementById('signFormModal');
    const title = document.getElementById('formTitle');

    if (signToEdit) {
        title.textContent = "Редагувати знак";
        document.getElementById('signId').value = signToEdit.id;
        document.getElementById('signName').value = signToEdit.name;
        document.getElementById('signCategory').value = signToEdit.category;
        document.getElementById('signDescription').value = signToEdit.description;
    } else {
        title.textContent = "Додати новий знак";
        document.getElementById('signId').value = '';
        document.getElementById('signName').value = '';
        document.getElementById('signCategory').value = '';
        document.getElementById('signDescription').value = '';
    }
    modal.style.display = 'flex';
}

// Перехід від вікна деталей до вікна редагування
async function editCurrentSign() {
    const name = document.getElementById('detailName').textContent;
    const category = document.getElementById('detailCategory').textContent;
    const description = document.getElementById('detailDescription').textContent;

    closeModal('detailModal');
    openSignForm({ id: currentSignId, name, category, description });
}

// Збереження (Створення або Оновлення)
async function saveSign() {
    const id = document.getElementById('signId').value;
    const name = document.getElementById('signName').value;
    const category = document.getElementById('signCategory').value;
    const description = document.getElementById('signDescription').value;

    const payload = { name, category, description };
    const method = id ? 'PATCH' : 'POST';
    const url = id ? `${API_URL}/signs/${id}` : `${API_URL}/signs`;

    let idemKey = null;
    if (!id) idemKey = await generateIdempotencyKey(payload);

    try {
        const res = await fetchWithResilience(url, {
            method: method,
            body: JSON.stringify(payload),
            idempotencyKey: idemKey
        });

        if (res.ok) {
            alert(id ? 'Знак оновлено!' : 'Знак створено!');
            closeModal('signFormModal');
            loadAllSigns();
        }
    } catch (e) {
        alert('Помилка збереження: ' + (e.error || e));
    }
}

// Видалення знака
async function deleteCurrentSign() {
    if (!confirm('Ви впевнені, що хочете видалити цей знак?')) return;

    try {
        const res = await fetchWithResilience(`${API_URL}/signs/${currentSignId}`, { method: 'DELETE' });
        if (res.ok || res.status === 204) {
            alert('Знак видалено');
            closeModal('detailModal');
            loadAllSigns();
        }
    } catch (e) {
        alert('Помилка видалення');
    }
}

// --- ІНШЕ (Auth, Tabs, Utils) ---

function openAuthModal() { document.getElementById('authModal').style.display = 'flex'; updateUI(); }
function closeModal(id) { document.getElementById(id).style.display = 'none'; }

async function login() {
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;
    try {
        const res = await fetch(`${API_URL}/login`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:u, password:p})});
        const d = await res.json();
        if(res.ok) {
            localStorage.setItem('access_token', d.access_token);
            localStorage.setItem('user', JSON.stringify(d.user));
            closeModal('authModal');
            updateUI();
            loadAllSigns();
        } else { alert(d.error); }
    } catch(e) {}
}

async function register() {
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;
    try { await fetch(`${API_URL}/register`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:u, password:p})}); alert('OK! Тепер увійдіть.'); } catch(e){}
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    updateUI();
    loadAllSigns();
}

function updateUI() {
    const user = JSON.parse(localStorage.getItem('user'));
    document.getElementById('authStatus').style.display = user ? 'block' : 'none';
    document.getElementById('authForm').style.display = user ? 'none' : 'block';

    if (user) {
        document.getElementById('authUsername').textContent = user.username;
    }

    // Кнопка додавання знака
    const addBtn = document.getElementById('addSignBtn');
    if (addBtn) {
        addBtn.style.display = (user && user.role === 'admin') ? 'inline-block' : 'none';
    }

    // Вкладка користувачів
    const userTabBtn = document.querySelectorAll('.tab')[1];
    if (userTabBtn) {
        userTabBtn.style.display = (user && user.role === 'admin') ? 'block' : 'none';
    }
}

function setLoading(id, state) { const el = document.getElementById(id); if(el) el.style.display = state ? 'block' : 'none'; }

async function loadSignsByCategory(cat) {
    setLoading('loading', true);
    try {
        const res = await fetchWithResilience(`${API_URL}/signs/${cat}`);
        const data = await res.json();
        displaySigns(data.data);
    } catch (e) {}
    setLoading('loading', false);
}

function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`${tab}-tab`).classList.add('active');

    const btns = document.querySelectorAll('.tab');
    if (tab === 'signs') { btns[0].classList.add('active'); loadAllSigns(); }
    if (tab === 'users') { btns[1].classList.add('active'); loadAllUsers(); }
}

async function loadAllUsers() {
    try {
        const res = await fetchWithResilience(`${API_URL}/users`);
        const data = await res.json();
        const c = document.getElementById('usersList');
        if(!c) return;
        c.innerHTML = '';
        data.data.forEach(u => {
            const d = document.createElement('div'); d.className = 'user-card';
            d.innerHTML = `<div><strong>${u.username}</strong> ${u.role}</div>`;
            const b = document.createElement('button'); b.className = 'promote-btn';
            b.textContent = u.is_admin ? 'Вже адмін' : 'Підвищити';
            b.disabled = u.is_admin;
            b.onclick = () => promoteUser(u.id);
            d.appendChild(b); c.appendChild(d);
        });
    } catch(e) {}
}

async function promoteUser(id) {
    try {
        await fetchWithResilience(`${API_URL}/users/${id}/promote`, {method:'POST'});
        loadAllUsers();
    } catch(e){}
}

// Тестова функція для ідемпотентності (залишена для демо)
async function createTestSign() {
    const payload = {
        name: "Тест " + Math.floor(Math.random() * 100),
        category: "Тестові",
        description: "Авто-тест"
    };
    const key = await generateIdempotencyKey(payload);
    try {
        const res = await fetchWithResilience(`${API_URL}/signs`, {
            method: 'POST', body: JSON.stringify(payload), idempotencyKey: key
        });
        const d = await res.json();
        alert(`ID: ${d.data.id}`);
        loadAllSigns();
    } catch (e) { alert('Помилка'); }
}

window.onload = () => { loadAllSigns(); updateUI(); };