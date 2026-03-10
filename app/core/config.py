import os


class Settings:
    def __init__(self) -> None:
        self.JWT_SECRET = os.getenv("JWT_SECRET", "")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


settings = Settings()
