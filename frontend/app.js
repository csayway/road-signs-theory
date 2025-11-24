const API_URL = 'http://localhost:5000';
let consecutiveFailures = 0;
const FAILURE_THRESHOLD = 3;

// === 1. SMART CLIENT (Resilient Fetch) ===

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// Експоненційний Backoff з Jitter (випадковістю)
const getBackoffDelay = (attempt, baseDelayMs = 300) => {
    const jitter = Math.floor(Math.random() * 100);
    return (baseDelayMs * (2 ** attempt)) + jitter;
};

// Головна функція-обгортка для запитів
async function fetchWithResilience(url, options = {}) {
    const { retries = 3, timeoutMs = 5000, idempotencyKey = null, ...fetchOptions } = options;

    const headers = new Headers(fetchOptions.headers || {});
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');

    // Додаємо X-Request-Id для відстеження (кореляції)
    if (!headers.has('X-Request-Id')) headers.set('X-Request-Id', crypto.randomUUID());

    // Додаємо Idempotency-Key для безпечних повторів POST-запитів
    if (idempotencyKey) headers.set('Idempotency-Key', idempotencyKey);

    // Автоматично додаємо токен авторизації
    const token = localStorage.getItem('access_token');
    if (token) headers.append('Authorization', `Bearer ${token}`);

    let attempt = 0;
    while (attempt <= retries) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            console.log(`📡 Запит ${url} (Спроба ${attempt + 1}/${retries + 1})`);
            const res = await fetch(url, { ...fetchOptions, headers, signal: controller.signal });
            clearTimeout(timeoutId);

            // Успіх
            if (res.ok) {
                resetDegradedMode();
                return res;
            }

            // 429 Too Many Requests: чекаємо стільки, скільки сказав сервер
            if (res.status === 429) {
                const retryAfter = res.headers.get('Retry-After');
                const wait = (retryAfter ? parseInt(retryAfter) : 1) * 1000;
                console.warn(`⚠ 429. Чекаємо ${wait}мс`);
                await sleep(wait);
                continue; // Повторюємо запит
            }

            // 5xx Server Errors: пробуємо ще раз із затримкою
            if (res.status >= 500 && attempt < retries) {
                const delay = getBackoffDelay(attempt);
                console.warn(` Помилка ${res.status}. Ретрай через ${delay}мс`);
                await sleep(delay);
                attempt++;
                continue;
            }

            // 401 Unauthorized: токен протух, виходимо
            if (res.status === 401) logout();

            // Інші помилки клієнта (400, 404 тощо) повертаємо відразу
            const errData = await res.json();
            handleDegradedMode();
            return Promise.reject(errData);

        } catch (err) {
            clearTimeout(timeoutId);
            console.error(' Помилка:', err.name === 'AbortError' ? 'Timeout' : err);

            // Мережеві помилки (або таймаут) теж пробуємо повторити
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

// === 2. HELPER FUNCTIONS (Idempotency & UI) ===

// Генерує унікальний ключ на основі даних (щоб не дублювати створення)
async function generateIdempotencyKey(payload) {
    const str = JSON.stringify(payload);
    const hashBuffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
    return Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 16);
}

// Вмикає "Деградований режим" (банер про перевантаження)
function handleDegradedMode() {
    consecutiveFailures++;
    if (consecutiveFailures >= FAILURE_THRESHOLD) {
        const banner = document.getElementById('degradedBanner');
        if (banner) banner.style.display = 'block';
        document.querySelectorAll('button').forEach(b => b.disabled = true);
    }
}

// Вимикає "Деградований режим"
function resetDegradedMode() {
    consecutiveFailures = 0;
    const banner = document.getElementById('degradedBanner');
    if (banner) banner.style.display = 'none';
    document.querySelectorAll('button').forEach(b => b.disabled = false);
}

// === 3. APP LOGIC ===

async function loadAllSigns() {
    setLoading('loading', true);
    try {
        const res = await fetchWithResilience(`${API_URL}/signs`);
        const data = await res.json();
        displaySigns(data.data);
    } catch (err) {
        document.getElementById('signsList').innerHTML = `<p style="color:red">Помилка: ${err.error || err.message}</p>`;
    }
    setLoading('loading', false);
}

// Тестова функція для перевірки Ідемпотентності
async function createTestSign() {
    const payload = {
        name: "Тест Ідемпотентності " + Math.floor(Math.random() * 100),
        category: "Тестові",
        description: "Цей запит не створить дублікатів"
    };
    const key = await generateIdempotencyKey(payload);
    console.log(" Generated Key:", key);

    try {
        const res = await fetchWithResilience(`${API_URL}/signs`, {
            method: 'POST',
            body: JSON.stringify(payload),
            idempotencyKey: key
        });
        const data = await res.json();
        alert(`Успіх! ID: ${data.data.id}`);
        loadAllSigns();
    } catch (err) {
        alert(`Помилка: ${err.error || 'Request Failed'}`);
    }
}

// --- Стандартні функції (без змін логіки, але з використанням нового fetch) ---

function setLoading(id, state) { const el = document.getElementById(id); if(el) el.style.display = state ? 'block' : 'none'; }

function displaySigns(signs) {
    const c = document.getElementById('signsList'); c.innerHTML = '';
    if(!signs) return;
    signs.forEach(s => {
        const d = document.createElement('div'); d.className = 'sign-card';
        d.innerHTML = `<span class="category">${s.category}</span><h3>${s.name}</h3><p>${s.description}</p>`;
        c.appendChild(d);
    });
}

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

    // Оновлення стилів кнопок
    const btns = document.querySelectorAll('.tab');
    if (tab === 'signs') { btns[0].classList.add('active'); loadAllSigns(); }
    if (tab === 'users') { btns[1].classList.add('active'); loadAllUsers(); }
}

async function loadAllUsers() {
    try {
        const res = await fetchWithResilience(`${API_URL}/users`);
        const data = await res.json();
        displayUsers(data.data);
    } catch(e) {}
}

function displayUsers(users) {
    const c = document.getElementById('usersList'); c.innerHTML = '';
    users.forEach(u => {
        const d = document.createElement('div'); d.className = 'user-card';
        d.innerHTML = `<div><strong>${u.username}</strong> ${u.role}</div>`;
        const b = document.createElement('button'); b.className = 'promote-btn';
        b.textContent = u.is_admin ? 'Вже адмін' : 'Підвищити';
        b.disabled = u.is_admin;
        b.onclick = () => promoteUser(u.id);
        d.appendChild(b);
        c.appendChild(d);
    });
}

async function promoteUser(id) {
    try { await fetchWithResilience(`${API_URL}/users/${id}/promote`, {method:'POST'}); loadAllUsers(); } catch(e){}
}

function openModal() { document.getElementById('authModal').style.display = 'flex'; updateUI(); }
function closeModal() { document.getElementById('authModal').style.display = 'none'; }

async function login() {
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;
    try {
        const res = await fetch(`${API_URL}/login`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:u, password:p})});
        const d = await res.json();
        if(res.ok) { localStorage.setItem('access_token', d.access_token); localStorage.setItem('user', JSON.stringify(d.user)); closeModal(); updateUI(); }
        else alert(d.error);
    } catch(e) {}
}

async function register() {
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;
    try { await fetch(`${API_URL}/register`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:u, password:p})}); alert('OK'); } catch(e){}
}

function logout() { localStorage.removeItem('access_token'); localStorage.removeItem('user'); updateUI(); switchTab('signs'); }

function updateUI() {
    const user = JSON.parse(localStorage.getItem('user'));
    const statusDiv = document.getElementById('authStatus');
    const formDiv = document.getElementById('authForm');

    if (user) {
        statusDiv.style.display = 'block';
        formDiv.style.display = 'none';
        document.getElementById('authUsername').textContent = user.username;

        // Керування видимістю вкладки "Користувачі"
        const userTabBtn = document.querySelectorAll('.tab')[1];
        if (userTabBtn) userTabBtn.style.display = user.role === 'admin' ? 'block' : 'none';
    } else {
        statusDiv.style.display = 'none';
        formDiv.style.display = 'block';
        const userTabBtn = document.querySelectorAll('.tab')[1];
        if (userTabBtn) userTabBtn.style.display = 'none';
    }
}

window.onload = () => { loadAllSigns(); updateUI(); };