from .base import get_db_connection
from domain.users.user import User, Admin


def _convert_to_user(row) -> User | Admin | None:
    """(Private) Конвертує рядок з БД в об'єкт User/Admin"""
    if not row:
        return None
    if row['role'] == 'admin':
        return Admin(
            id=row['id'],
            username=row['username'],
            email=None
        )
    else:
        return User(
            id=row['id'],
            username=row['username'],
            email=None,
            role=row['role']
        )


class UserRepository:

    def get_all(self) -> list[User]:
        """Отримати всіх користувачів (без хешів паролів)"""
        conn = get_db_connection()
        rows = conn.execute("SELECT id, username, role FROM users").fetchall()
        conn.close()
        return [_convert_to_user(row) for row in rows]

    def get_by_id(self, user_id: int) -> User | None:
        """Отримати користувача за ID (безпечно, без хешу)"""
        conn = get_db_connection()
        row = conn.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return _convert_to_user(row)

    def get_by_username_for_auth(self, username: str) -> dict | None:
        """
        Отримати повні дані (включаючи хеш!) для логіну.
        Повертає dict, а не доменну модель, бо хеш - це деталь інфраструктури.
        """
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        return row  # row - це вже dict, завдяки row_factory

    def create(self, username: str, hashed_password: str, role: str = 'guest') -> None:
        """Створити нового користувача"""
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hashed_password, role)
        )
        conn.commit()
        conn.close()

    def update_role(self, user_id: int, new_role: str) -> None:
        """Оновити роль користувача"""
        conn = get_db_connection()
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        conn.close()