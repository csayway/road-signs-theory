class RoadSign:
    def __init__(self, id: int, name: str, category: str, description: str = None, image_url: str = None):
        self.id = id
        self.name = name
        self.category = category
        self.description = description
        self.image_url = image_url

    def update_description(self, new_description: str):
        """Оновити опис дорожнього знака"""
        self.description = new_description

    def change_category(self, new_category: str):
        """Змінити категорію знака"""
        self.category = new_category

    def to_dict(self):
        """Конвертує об'єкт в словник для JSON-серіалізації"""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'image_url': self.image_url
        }


class SignCategory:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.signs = []  # Список знаків у цій категорії

    def add_sign(self, sign: RoadSign):
        """Додати знак до категорії"""
        self.signs.append(sign)

    def get_signs_count(self) -> int:
        """Отримати кількість знаків у категорії"""
        return len(self.signs)