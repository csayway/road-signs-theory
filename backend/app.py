import sqlite3
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from functools import wraps

from repositories.road_sign import RoadSignRepository
from repositories.user import UserRepository

# Імпорти доменних моделей (для демонстрації)
from domain.catalog.road_sign import RoadSign
from domain.users.user import User

app = Flask(__name__)
CORS(app, resources={r"/*": {
    "origins": "*",
    "allow_headers": ["Content-Type", "Authorization"]
}})

# --- Налаштування ---
app.config["JWT_SECRET_KEY"] = "ezhi"
app.config["SECRET_KEY"] = "super-secret-flask-key-change-me"
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# --- Створюємо екземпляри репозиторіїв ---
sign_repo = RoadSignRepository()
user_repo = UserRepository()
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'road_signs.db')


def init_database():
    """Ініціалізація бази даних"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # --- ОНОВЛЕНО: Повні схеми таблиць ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS road_signs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, 
            role TEXT DEFAULT 'guest',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM road_signs")
    count_signs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    count_users = cursor.fetchone()[0]

    if count_signs == 0:
        signs = [
            ('Стоп', 'Заборонні', 'Зупинитися перед знаком'),
            ('Головна дорога', 'Пріоритету', 'Перевага на перехресті'),
            ('Пішохідний перехід', 'Інформаційні', 'Місце переходу для пішоходів'),
            ('Обмеження швидкості 50', 'Заборонні', 'Максимальна швидкість 50 км/год'),
            ('Поворот праворуч', 'Попереджувальні', 'Попередження про поворот'),
            ('Діти', 'Попереджувальні', 'Можлива поява дітей на дорозі'),
            ('Парковка', 'Інформаційні', 'Місце для парковки'),
            ('Рух заборонено', 'Заборонні', 'Заборона руху всіх транспортних засобів')
        ]

        cursor.executemany(
            "INSERT INTO road_signs (name, category, description) VALUES (?, ?, ?)",
            signs
        )
        print(" Дані дорожніх знаків успішно додані до бази!")

    if count_users == 0:
        users = [
            ('admin', bcrypt.generate_password_hash('admin123').decode('utf-8'), 'admin'),
            ('user1', bcrypt.generate_password_hash('user123').decode('utf-8'), 'guest'),
        ]
        cursor.executemany(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            users
        )
        print("Тестові користувачі (з хешованими паролями) додані до бази!")

    conn.commit()
    conn.close()


# --- ВИДАЛЕНО ---
# get_db_connection() - переїхав у repositories/base.py
# convert_to_road_sign() - переїхав у repositories/road_sign.py
# convert_to_user() - переїхав у repositories/user.py
# ---


# Функція-декоратор для перевірки прав адміна
def admin_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            current_user_id_str = get_jwt_identity()

            # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
            user = user_repo.get_by_id(int(current_user_id_str))

            if user and user.is_admin():
                return fn(*args, **kwargs)
            else:
                return jsonify({"error": "Admin access required"}), 403

        return decorator

    return wrapper


# --- ЕНДПОІНТИ ДЛЯ ЗНАКІВ ---
@app.route('/')
def home():
    return jsonify({"message": "Довідник дорожніх знаків API"})


@app.route('/signs', methods=['GET'])
def get_all_signs():
    try:
        # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
        road_signs = sign_repo.get_all()
        # ВИКОРИСТОВУЄМО .to_dict()
        return jsonify({'message': 'success', 'data': [s.to_dict() for s in road_signs]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/signs/<category>', methods=['GET'])
def get_signs_by_category(category):
    try:
        # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
        road_signs = sign_repo.get_by_category(category)
        return jsonify({
            'message': 'success',
            'category': category,
            'data': [s.to_dict() for s in road_signs]  # ВИКОРИСТОВУЄМО .to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/signs/id/<int:sign_id>', methods=['GET'])
def get_sign_by_id(sign_id):
    try:
        # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
        sign = sign_repo.get_by_id(sign_id)
        if sign:
            return jsonify({'message': 'success', 'data': sign.to_dict()})  # ВИКОРИСТОВУЄМО .to_dict()
        else:
            return jsonify({'error': 'Sign not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/signs', methods=['POST'])
@admin_required()
def create_sign():
    data = request.get_json()
    name = data.get('name')
    category = data.get('category')
    description = data.get('description')

    if not name or not category:
        return jsonify({
            "error": "Validation Error",
            "code": "SIGN_FIELDS_REQUIRED",
            "details": [{"field": "name", "message": "Name and category are required"}]
        }), 400

    try:
        # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
        new_sign = sign_repo.create(name, category, description)
        return jsonify({'message': 'success', 'data': new_sign.to_dict()}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/signs/id/<int:sign_id>', methods=['PATCH'])
@admin_required()
def update_sign(sign_id):
    data = request.get_json()

    # Перевірка, чи передано хоча б одне поле для оновлення
    if not data:
        return jsonify({
            "error": "Validation Error",
            "code": "NO_DATA_PROVIDED",
            "details": [{"message": "No fields provided for update"}]
        }), 400

    try:
        # 1. Перевіряємо, чи існує
        existing_sign = sign_repo.get_by_id(sign_id)
        if not existing_sign:
            return jsonify({'error': 'Sign not found'}), 404

        # 2. Оновлюємо в базі (репозиторій)
        sign_repo.update(sign_id, data)

        # 3. Повертаємо оновлений об'єкт
        updated_sign = sign_repo.get_by_id(sign_id)

        return jsonify({'message': 'success', 'data': updated_sign.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/signs/id/<int:sign_id>', methods=['DELETE'])
@admin_required()
def delete_sign(sign_id):
    try:
        # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
        rows_deleted = sign_repo.delete(sign_id)

        if rows_deleted == 0:
            return jsonify({'error': 'Sign not found'}), 404

        # 204 No Content - ідеальна відповідь для DELETE
        return '', 204

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- ЕНДПОІНТИ АВТЕНТИФІКАЦІЇ ---

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
    existing_user = user_repo.get_by_username_for_auth(username)
    if existing_user:
        return jsonify({"error": "Username already exists"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
    user_repo.create(username, hashed_password, 'guest')
    return jsonify({"message": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
    user_row = user_repo.get_by_username_for_auth(username)

    if user_row and bcrypt.check_password_hash(user_row['password_hash'], password):
        access_token = create_access_token(identity=str(user_row['id']))
        return jsonify(
            message="Login successful",
            access_token=access_token,
            user={
                'id': user_row['id'],
                'username': user_row['username'],
                'role': user_row['role']
            }
        )
    else:
        return jsonify({"error": "Invalid username or password"}), 401


# --- ЕНДПОІНТИ ДЛЯ КОРИСТУВАЧІВ ---

@app.route('/users', methods=['GET'])
@admin_required()
def get_all_users():
    try:
        # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
        users = user_repo.get_all()
        return jsonify({'message': 'success', 'data': [u.to_dict() for u in users]})  # ВИКОРИСТОВУЄМО .to_dict()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users/<int:user_id>', methods=['GET'])
@admin_required()
def get_user_by_id(user_id):
    try:
        # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ
        user = user_repo.get_by_id(user_id)
        if user:
            return jsonify({'message': 'success', 'data': user.to_dict()})  # ВИКОРИСТОВУЄМО .to_dict()
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users/<int:user_id>/promote', methods=['POST'])
@admin_required()
def promote_user_to_admin(user_id):
    try:
        # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ (Крок 1: Отримати об'єкт)
        user = user_repo.get_by_id(user_id)
        if user:
            # ВИКОРИСТОВУЄМО DDD МОДЕЛЬ (Крок 2: Змінити стан)
            user.promote_to_admin()

            # ВИКОРИСТОВУЄМО РЕПОЗИТОРІЙ (Крок 3: Зберегти стан)
            user_repo.update_role(user.id, user.role)

            return jsonify({'message': 'success', 'user': user.to_dict()})  # ВИКОРИСТОВУЄМО .to_dict()
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Повертає статус системи"""
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    if os.path.exists(DATABASE_PATH):
        print(f"Видаляємо стару базу {DATABASE_PATH} для оновлення структури...")
        os.remove(DATABASE_PATH)

    init_database()

    # Демонстрація DDD моделей
    print("Демонстрація DDD моделей:")
    demo_sign = RoadSign(1, "Стоп", "Заборонні", "Зупинитися перед знаком")
    print(f"   Створено знак: {demo_sign.name}")
    demo_user = User(1, "test_user", "test@example.com", "guest")
    print(f"   Створено користувача: {demo_user.username}")
    demo_user.promote_to_admin()
    print(f"   Після підвищення: {demo_user.role}")

    app.run(debug=True, port=5000)