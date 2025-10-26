const API_URL = 'http://localhost:5000';
let currentUsers = [];

// --- НОВІ ФУНКЦІЇ ДЛЯ РОБОТИ З ТОКЕНОМ (localStorage) ---

function saveToken(token) {
    localStorage.setItem('access_token', token);
}

function getToken() {
    return localStorage.getItem('access_token');
}

function removeToken() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user'); // Також чистимо інфо про юзера
}

function saveUser(user) {
    localStorage.setItem('user', JSON.stringify(user));
}

function getUser() {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
}

function isLoggedIn() {
    return !!getToken();
}

// --- НОВА ФУНКЦІЯ ДЛЯ ОНОВЛЕННЯ UI ---

function updateUI() {
    const userTab = document.querySelector('.tab[onclick="switchTab(\'users\')"]');
    const authStatus = document.getElementById('authStatus');
    const authForm = document.getElementById('authForm');
    const authUsername = document.getElementById('authUsername');

    if (isLoggedIn()) {
        const user = getUser();

        // Показуємо статус "Ви увійшли як..."
        authStatus.style.display = 'block';
        authForm.style.display = 'none';
        authUsername.textContent = user.username;

        // Показуємо вкладку "Користувачі" ТІЛЬКИ якщо це адмін
        if (user && user.role === 'admin') {
            userTab.style.display = 'block';
        } else {
            userTab.style.display = 'none';
        }
    } else {
        // Ховаємо статус
        authStatus.style.display = 'none';
        authForm.style.display = 'block';

        // Ховаємо вкладку "Користувачі"
        userTab.style.display = 'none';
    }
}

// --- НОВА ФУНКЦІЯ ДЛЯ ЗАХИЩЕНИХ ЗАПИТІВ ---

async function fetchProtected(url, options = {}) {
    const token = getToken();

    // Створюємо заголовки, якщо їх немає
    if (!options.headers) {
        options.headers = new Headers();
    }

    // Додаємо токен
    if (token) {
        options.headers.append('Authorization', `Bearer ${token}`);
    }

    // Додаємо 'Content-Type' для POST запитів, якщо потрібно
    if (options.method === 'POST' && !options.headers.has('Content-Type')) {
        options.headers.append('Content-Type', 'application/json');
    }

    try {
        const res = await fetch(url, options);

        if (res.status === 401 || res.status === 403) {
            // Якщо токен недійсний або його немає - "викидаємо" юзера
            alert('Помилка авторизації. Будь ласка, увійдіть знову.');
            logout();
            return null; // Повертаємо null, щоб обробник не продовжив роботу
        }

        return res;
    } catch (err) {
        console.error('Fetch error:', err);
        throw err; // Кидаємо помилку далі
    }
}


// --- ОНОВЛЕНІ ФУНКЦІЇ ---

function setLoading(elementId, state) {
    document.getElementById(elementId).style.display = state ? 'block' : 'none';
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.getElementById(tabName + '-tab').classList.add('active');

    // Знаходимо кнопку табу і робимо її активною
    const tabButton = document.querySelector(`.tab[onclick="switchTab('${tabName}')"]`);
    if(tabButton) tabButton.classList.add('active');

    if (tabName === 'users') loadAllUsers();
}

async function loadAllSigns() {
    setLoading('loading', true);
    try {
        // Це публічний ендпоінт, токен не потрібен
        const res = await fetch(`${API_URL}/signs`);
        const data = await res.json();
        displaySigns(data.data);
    } catch (err) {
        // Пишемо помилку у контейнер для ЗНАКІВ
        document.getElementById('signsList').innerHTML = '<p>Помилка завантаження</p>';
    }
    setLoading('loading', false);
}

async function loadSignsByCategory(cat) {
    setLoading('loading', true);
    try {
        // Це публічний ендпоінт
        const res = await fetch(`${API_URL}/signs/${cat}`);
        const data = await res.json();
        displaySigns(data.data);
    } catch (err) {
        document.getElementById('signsList').innerHTML = '<p>Помилка завантаження</p>';
    }
    setLoading('loading', false);
}

// Безпечна displaySigns (без змін)
function displaySigns(signs) {
    const container = document.getElementById('signsList');
    container.innerHTML = '';
    if (!signs || !signs.length) {
        container.innerHTML = '<p>Знаки не знайдено</p>';
        return;
    }
    signs.forEach(sign => {
        const card = document.createElement('div');
        card.className = 'sign-card';
        const category = document.createElement('span');
        category.className = 'category';
        category.textContent = sign.category;
        const name = document.createElement('h3');
        name.textContent = sign.name;
        const description = document.createElement('p');
        description.textContent = sign.description;
        card.appendChild(category);
        card.appendChild(name);
        card.appendChild(description);
        container.appendChild(card);
    });
}

// ОНОВЛЕНО: Використовуємо fetchProtected
async function loadAllUsers() {
    setLoading('usersLoading', true);
    try {
        // ЦЕ ЗАХИЩЕНИЙ ЗАПИТ
        const res = await fetchProtected(`${API_URL}/users`);
        if (!res) return; // Вихід, якщо була помилка авторизації

        const data = await res.json();
        if(res.ok) {
            currentUsers = data.data;
            displayUsers(currentUsers);
        } else {
            document.getElementById('usersList').innerHTML = `<p>Помилка: ${data.error || data.msg || 'Невідома помилка'}</p>`;
        }
    } catch (err) {
        document.getElementById('usersList').innerHTML = '<p>Помилка завантаження користувачів</p>';
    }
    setLoading('usersLoading', false);
}

// Безпечна displayUsers (без змін)
function displayUsers(users) {
    const container = document.getElementById('usersList');
    container.innerHTML = '';
    if (!users || !users.length) {
        container.innerHTML = '<p>Користувачі не знайдені</p>';
        return;
    }
    users.forEach(user => {
        const card = document.createElement('div');
        card.className = 'user-card';
        const info = document.createElement('div');
        const username = document.createElement('strong');
        username.textContent = user.username;
        const email = document.createTextNode(` (Роль: ${user.role}) `); // Оновив текст
        const badge = document.createElement('span');
        badge.className = user.is_admin ? 'admin-badge' : 'guest-badge';
        badge.textContent = user.is_admin ? 'Адміністратор' : 'Гість';
        info.appendChild(username);
        // info.appendChild(email); // Можна додати, якщо треба
        info.appendChild(badge);
        const promoteBtn = document.createElement('button');
        promoteBtn.className = 'promote-btn';
        promoteBtn.textContent = user.is_admin ? 'Вже адмін' : 'Зробити адміном';
        promoteBtn.disabled = user.is_admin;
        promoteBtn.addEventListener('click', () => {
            promoteUser(user.id);
        });
        card.appendChild(info);
        card.appendChild(promoteBtn);
        container.appendChild(card);
    });
}

// ОНОВЛЕНО: Використовуємо fetchProtected
async function promoteUser(id) {
    try {
        // ЦЕ ЗАХИЩЕНИЙ ЗАПИТ
        const res = await fetchProtected(`${API_URL}/users/${id}/promote`, { method: 'POST' });
        if (!res) return; // Вихід, якщо була помилка авторизації

        const result = await res.json();
        if (res.ok) {
            alert('Користувача підвищено до адміністратора!');
            loadAllUsers(); // Оновлюємо список
        } else {
            alert(`Помилка: ${result.error}`);
        }
    } catch (err) {
        alert('Сталася помилка при підвищенні прав');
    }
}

function openModal() {
    document.getElementById('authModal').style.display = 'flex';
    updateUI(); // Оновлюємо вигляд модалки при кожному відкритті
}

function closeModal() {
    document.getElementById('authModal').style.display = 'none';
}

// --- НОВА ЛОГІКА ВХОДУ / РЕЄСТРАЦІЇ / ВИХОДУ ---

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!username || !password) {
        alert('Введіть ім\'я користувача та пароль');
        return;
    }

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (res.ok) {
            // ВХІД УСПІШНИЙ
            saveToken(data.access_token);
            saveUser(data.user);
            alert('Вхід виконано успішно!');
            closeModal();
            updateUI(); // Оновлюємо таби
        } else {
            // ПОМИЛКА ВХОДУ
            alert(`Помилка входу: ${data.error}`);
        }
    } catch (err) {
        alert('Сталася помилка мережі');
    }
}

async function register() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!username || !password) {
        alert('Введіть ім\'я користувача та пароль');
        return;
    }

    try {
        const res = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (res.status === 201) {
            // РЕЄСТРАЦІЯ УСПІШНА
            alert('Користувача успішно створено! Тепер можете увійти.');
            // (Опціонально) можна одразу логінити юзера
        } else {
            // ПОМИЛКА РЕЄСТРАЦІЇ
            alert(`Помилка реєстрації: ${data.error}`);
        }
    } catch (err) {
        alert('Сталася помилка мережі');
    }
}

function logout() {
    removeToken();
    alert('Ви вийшли з системи.');
    updateUI();
    // Опціонально: перемикаємо на головну вкладку, якщо ми були на адмінській
    switchTab('signs');
}


// ОНОВЛЕНО: При завантаженні сторінки
window.onload = () => {
    loadAllSigns(); // Завантажуємо знаки
    updateUI();     // Оновлюємо UI (ховаємо адмін-вкладку, якщо треба)
};