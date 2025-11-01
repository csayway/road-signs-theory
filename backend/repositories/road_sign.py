from .base import get_db_connection
from domain.catalog.road_sign import RoadSign


def _convert_to_road_sign(row):
    """(Private) Конвертує рядок з БД в об'єкт RoadSign"""
    return RoadSign(
        id=row['id'],
        name=row['name'],
        category=row['category'],
        description=row['description']
    )


class RoadSignRepository:

    def get_all(self) -> list[RoadSign]:
        """Отримати всі знаки з БД"""
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM road_signs").fetchall()
        conn.close()
        return [_convert_to_road_sign(row) for row in rows]

    def get_by_category(self, category: str) -> list[RoadSign]:
        """Отримати знаки за категорією"""
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM road_signs WHERE category = ?", (category,)).fetchall()
        conn.close()
        return [_convert_to_road_sign(row) for row in rows]

    def get_by_id(self, sign_id: int) -> RoadSign | None:
        """Отримати один знак за ID"""
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM road_signs WHERE id = ?", (sign_id,)).fetchone()
        conn.close()
        return _convert_to_road_sign(row) if row else None

    def create(self, name: str, category: str, description: str = None) -> RoadSign:
        """Створити новий знак і повернути його об'єкт."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO road_signs (name, category, description) VALUES (?, ?, ?)",
            (name, category, description)
        )
        last_id = cursor.lastrowid
        conn.commit()

        # Отримуємо створений об'єкт, щоб повернути його у відповідь
        created_row = conn.execute("SELECT * FROM road_signs WHERE id = ?", (last_id,)).fetchone()
        conn.close()
        return _convert_to_road_sign(created_row)

    def update(self, sign_id: int, data: dict) -> None:
        """Оновити наявний знак за ID."""
        conn = get_db_connection()
        # Створюємо динамічний SQL-запит
        set_clauses = [f"{k} = ?" for k in data.keys()]
        query = f"UPDATE road_signs SET {', '.join(set_clauses)} WHERE id = ?"
        params = list(data.values()) + [sign_id]

        conn.execute(query, params)
        conn.commit()
        conn.close()

    def delete(self, sign_id: int) -> int:
        """Видалити знак за ID і повернути кількість видалених рядків (0 або 1)."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM road_signs WHERE id = ?", (sign_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected