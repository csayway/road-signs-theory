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