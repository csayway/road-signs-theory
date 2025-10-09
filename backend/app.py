from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)  # Дозволяє запити з фронтенду

# Шлях до бази даних
DATABASE = 'data/road_signs.db'


def init_database():
    """Ініціалізація бази даних"""
    os.makedirs('data', exist_ok=True)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Створюємо таблицю
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS road_signs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT
        )
    ''')

    # Перевіряємо чи є дані
    cursor.execute("SELECT COUNT(*) FROM road_signs")
    count = cursor.fetchone()[0]

    if count == 0:
        # Додаємо тестові дані
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
        print("Дані успішно додані до бази!")

    conn.commit()
    conn.close()


def get_db_connection():
    """Підключення до бази даних"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Повертає результати у вигляді словника
    return conn


# Головна сторінка
@app.route('/')
def home():
    return jsonify({"message": "Довідник дорожніх знаків API"})


# Ендпоінт для отримання всіх знаків
@app.route('/signs', methods=['GET'])
def get_all_signs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM road_signs")
        signs = cursor.fetchall()

        # Конвертуємо в список словників
        signs_list = []
        for sign in signs:
            signs_list.append({
                'id': sign['id'],
                'name': sign['name'],
                'category': sign['category'],
                'description': sign['description']
            })

        conn.close()
        return jsonify({
            'message': 'success',
            'data': signs_list
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Ендпоінт для отримання знаків за категорією
@app.route('/signs/<category>', methods=['GET'])
def get_signs_by_category(category):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM road_signs WHERE category = ?", (category,))
        signs = cursor.fetchall()

        signs_list = []
        for sign in signs:
            signs_list.append({
                'id': sign['id'],
                'name': sign['name'],
                'category': sign['category'],
                'description': sign['description']
            })

        conn.close()
        return jsonify({
            'message': 'success',
            'data': signs_list
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_database()  # Ініціалізуємо БД при запуску
    app.run(debug=True, port=5000)