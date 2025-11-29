import sqlite3
import os
import time
import random
import uuid
from flask import Flask, jsonify, request, make_response, g
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from functools import wraps
from werkzeug.exceptions import HTTPException

# Імпорти репозиторіїв
from repositories.road_sign import RoadSignRepository
from repositories.user import UserRepository

# Імпорти доменних моделей
from domain.catalog.road_sign import RoadSign
from domain.users.user import User

app = Flask(__name__)

# --- КОНФІГУРАЦІЯ ---
app.config["JWT_SECRET_KEY"] = "ezhi"
app.config["SECRET_KEY"] = "super-secret-flask-key-change-me"

# Дозволяємо браузеру бачити спеціальні заголовки (Retry-After, X-Request-Id)
CORS(app, resources={r"/*": {
    "origins": "*",
    "allow_headers": ["Content-Type", "Authorization", "Idempotency-Key", "X-Request-Id"],
    "expose_headers": ["Retry-After", "X-Request-Id"]
}})

jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# --- Створюємо екземпляри репозиторіїв ---
sign_repo = RoadSignRepository()
user_repo = UserRepository()
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'road_signs.db')

# --- In-Memory сховища (для демонстрації) ---
idempotency_store = {}  # Key -> {status, response_body}
rate_limit_store = {}  # IP -> {count, start_time}
RATE_LIMIT_WINDOW = 10
MAX_REQUESTS = 20


# --- MIDDLEWARE: X-Request-Id ---
@app.before_request
def add_request_id():
    # Беремо ID з заголовка клієнта або генеруємо новий
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    g.request_id = request_id


@app.after_request
def inject_request_id(response):
    # Додаємо ID у відповідь для кореляції логів
    response.headers["X-Request-Id"] = g.get("request_id", "unknown")
    return response


# --- MIDDLEWARE: Єдиний формат помилки ---
@app.errorhandler(Exception)
def handle_exception(e):
    code = 500
    error_name = "Internal Server Error"
    details = str(e)

    if isinstance(e, HTTPException):
        code = e.code
        error_name = e.name
        details = e.description

    return jsonify({
        "error": error_name,
        "code": getattr(e, "code", "UNKNOWN_ERROR"),
        "details": details,
        "requestId": g.get("request_id")
    }), code


# --- MIDDLEWARE: Rate Limiting & Fault Injection (Хаос) ---
@app.before_request
def check_limits_and_chaos():
    # 1. Rate Limiting
    ip = request.remote_addr
    current_time = time.time()

    record = rate_limit_store.get(ip, {"count": 0, "start_time": current_time})

    if current_time - record["start_time"] > RATE_LIMIT_WINDOW:
        record = {"count": 1, "start_time": current_time}
    else:
        record["count"] += 1

    rate_limit_store[ip] = record

    if record["count"] > MAX_REQUESTS:
        retry_after = 5
        resp = make_response(jsonify({
            "error": "Too Many Requests",
            "code": "RATE_LIMIT_EXCEEDED",
            "details": "Please wait before retrying",
            "requestId": g.request_id
        }), 429)
        resp.headers["Retry-After"] = str(retry_after)
        return resp

    # 2. Fault Injection (Тільки для POST/PATCH, щоб тестувати ретраї)
    if request.method in ['POST', 'PATCH'] and "signs" in request.path:
        r = random.random()
        # 15% шанс затримки (simulated network lag)
        if r < 0.15:
            time.sleep(random.uniform(1.2, 2.0))
        # 10% шанс помилки 503/500
        if r > 0.90:
            err_type = "Service Unavailable" if random.random() < 0.5 else "Unexpected Error"
            status = 503 if err_type == "Service Unavailable" else 500
            # Викидаємо помилку, яку перехопить handle_exception, або повертаємо response вручну
            # Тут краще вручну, щоб контролювати статус
            return make_response(jsonify({
                "error": err_type,
                "requestId": g.request_id
            }), status)


def init_database():
    """Ініціалізація бази даних"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS road_signs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL, description TEXT)''')
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT DEFAULT 'guest', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute("SELECT COUNT(*) FROM road_signs")
    if cursor.fetchone()[0] == 0:
        signs = [('Стоп', 'Заборонні', 'Зупинитися перед знаком'),
                 ('Головна дорога', 'Пріоритету', 'Перевага на перехресті')]
        cursor.executemany("INSERT INTO road_signs (name, category, description) VALUES (?, ?, ?)", signs)

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [('admin', bcrypt.generate_password_hash('admin123').decode('utf-8'), 'admin')]
        cursor.executemany("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", users)

    conn.commit()
    conn.close()


# Функція-декоратор для перевірки прав адміна
def admin_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            current_user_id_str = get_jwt_identity()
            user = user_repo.get_by_id(int(current_user_id_str))
            if user and user.is_admin():
                return fn(*args, **kwargs)
            else:
                return jsonify({"error": "Admin access required", "requestId": g.get("request_id")}), 403

        return decorator

    return wrapper


# --- ROUTES ---

@app.route('/health', methods=['GET'])
def health_check():
    # Симулюємо іноді довгий запит для перевірки таймауту клієнта
    if random.random() < 0.1:
        time.sleep(2)
    return jsonify({"status": "ok", "requestId": g.request_id})


@app.route('/signs', methods=['GET'])
def get_all_signs():
    return jsonify({'message': 'success', 'data': [s.to_dict() for s in sign_repo.get_all()]})


@app.route('/signs/<category>', methods=['GET'])
def get_signs_by_category(category):
    return jsonify({'message': 'success', 'data': [s.to_dict() for s in sign_repo.get_by_category(category)]})


@app.route('/signs/id/<int:sign_id>', methods=['GET'])
def get_sign_by_id(sign_id):
    sign = sign_repo.get_by_id(sign_id)
    if sign: return jsonify({'message': 'success', 'data': sign.to_dict()})
    return jsonify({'error': 'Sign not found'}), 404


# --- POST З ІДЕМПОТЕНТНІСТЮ ---
@app.route('/signs', methods=['POST'])
@admin_required()
def create_sign():
    # 1. Перевірка ключа ідемпотентності
    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        return jsonify({
            "error": "Validation Error",
            "code": "IDEMPOTENCY_KEY_REQUIRED",
            "details": "Header Idempotency-Key is missing"
        }), 400

    # 2. Перевірка кешу
    if idem_key in idempotency_store:
        print(f" Повертаємо кешовану відповідь для {idem_key}")
        return jsonify(idempotency_store[idem_key]), 201

    data = request.get_json()
    name = data.get('name')
    category = data.get('category')
    description = data.get('description')

    if not name or not category:
        return jsonify({"error": "Validation Error"}), 400

    new_sign = sign_repo.create(name, category, description)
    response_data = {'message': 'success', 'data': new_sign.to_dict()}

    # 3. Збереження результату
    idempotency_store[idem_key] = response_data

    return jsonify(response_data), 201


@app.route('/signs/<int:sign_id>', methods=['PATCH'])
@admin_required()
def update_sign(sign_id):
    data = request.get_json()
    if not sign_repo.get_by_id(sign_id): return jsonify({'error': 'Not found'}), 404
    sign_repo.update(sign_id, data)
    return jsonify({'message': 'success', 'data': sign_repo.get_by_id(sign_id).to_dict()})


@app.route('/signs/<int:sign_id>', methods=['DELETE'])
@admin_required()
def delete_sign(sign_id):
    if sign_repo.delete(sign_id) == 0: return jsonify({'error': 'Not found'}), 404
    return '', 204


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if user_repo.get_by_username_for_auth(data.get('username')):
        return jsonify({"error": "Username exists"}), 409
    hashed = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
    user_repo.create(data.get('username'), hashed, 'guest')
    return jsonify({"message": "User registered"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user_row = user_repo.get_by_username_for_auth(data.get('username'))
    if user_row and bcrypt.check_password_hash(user_row['password_hash'], data.get('password')):
        access_token = create_access_token(identity=str(user_row['id']))
        return jsonify(message="Login successful", access_token=access_token,
                       user={'id': user_row['id'], 'username': user_row['username'], 'role': user_row['role']})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/users', methods=['GET'])
@admin_required()
def get_all_users():
    return jsonify({'message': 'success', 'data': [u.to_dict() for u in user_repo.get_all()]})


@app.route('/users/<int:user_id>/promote', methods=['POST'])
@admin_required()
def promote_user_to_admin(user_id):
    user = user_repo.get_by_id(user_id)
    if not user: return jsonify({'error': 'Not found'}), 404
    user.promote_to_admin()
    user_repo.update_role(user.id, user.role)
    return jsonify({'message': 'success', 'user': user.to_dict()})


if __name__ == '__main__':
    if os.path.exists(DATABASE_PATH):
        try:
            os.remove(DATABASE_PATH)
        except:
            pass
    init_database()
    app.run(debug=True, port=5000, host='0.0.0.0')