from decouple import config


class Config:
	BOT_TOKEN: str = config("BOT_TOKEN")


class DatabaseConfig:
	pass
