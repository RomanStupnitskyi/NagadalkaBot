from typing import Any
from datetime import datetime
from pymongo import MongoClient


def get_sorted_users(database_client: MongoClient) -> dict[str, Any]:
	users = [*database_client.user.data.find()]
	users.sort(key=user_key)
	return users

def user_key(user_data: dict[str, Any]) -> int:
	now = datetime.now()
	birthday = user_data['birthday']
	current_birthday = datetime(now.year, birthday.month, birthday.day)

	if now.timestamp() >= (current_birthday.timestamp()):
		current_birthday = datetime(now.year+1, birthday.month, birthday.day)

	return current_birthday.timestamp() - datetime.now().timestamp()
