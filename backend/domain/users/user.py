class User:
    # ОНОВЛЕНО: 'email' тепер опціональний (email: str = None)
    def __init__(self, id: int, username: str, email: str = None, role: str = "guest"):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

    def is_admin(self) -> bool:
        """Перевірити, чи є користувач адміністратором"""
        return self.role == "admin"

    def promote_to_admin(self):
        """Повисити права до адміністратора"""
        self.role = "admin"

    # НОВИЙ МЕТОД
    def to_dict(self):
        """Конвертує об'єкт в словник для JSON-серіалізації"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_admin': self.is_admin()
        }


class Admin(User):
    # ОНОВЛЕНО: 'email' тепер опціональний (email: str = None)
    def __init__(self, id: int, username: str, email: str = None):
        super().__init__(id, username, email, "admin")

    def can_manage_content(self) -> bool:
        """Перевірити право на управління контентом"""
        return True