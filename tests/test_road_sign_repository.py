import pytest
import sqlite3
from unittest.mock import patch

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from repositories.road_sign import RoadSignRepository


# --- Налаштування Тестової Бази Даних ---

@pytest.fixture
def mock_db():
    # 1. Використовуємо спільну БД в пам'яті
    db_path = "file::memory:?cache=shared"

    conn_init = sqlite3.connect(db_path, uri=True)
    conn_init.row_factory = sqlite3.Row
    cursor = conn_init.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS road_signs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT
        )
    ''')
    conn_init.commit()


    # 3. буде викликатися замість справжньої get_db_connection
    def get_mocked_connection():
        # Вона створює нове, окреме з'єднання з тією ж БД в пам'яті
        conn = sqlite3.connect(db_path, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    # get_db_connection, щоб він викликав нашу функцію
    with patch('repositories.road_sign.get_db_connection', side_effect=get_mocked_connection) as mock_get_conn:
        yield mock_get_conn  # Тест виконується тут

    conn_init.close()


# --- Тести ---

def test_create_sign_success(mock_db):
    """Перевіряємо, що ми можемо створити, і отримати знак."""
    # 1. Підготовка
    repo = RoadSignRepository()

    # 2. Дія
    created_sign = repo.create(
        name="Тестовий Знак",
        category="Тестові",
        description="Опис"
    )

    # 3. Перевірка
    assert created_sign.id == 1
    assert created_sign.name == "Тестовий Знак"

    # Перевіряємо, що він в базі
    retrieved_sign = repo.get_by_id(1)
    assert retrieved_sign is not None
    assert retrieved_sign.name == "Тестовий Знак"


def test_get_by_id_error_case(mock_db):
    """Перевіряємо, що get_by_id повертає None, якщо знак не знайдено."""
    # 1. Підготовка
    repo = RoadSignRepository()

    # 2. Дія
    retrieved_sign = repo.get_by_id(999)

    # 3. Перевірка
    assert retrieved_sign is None