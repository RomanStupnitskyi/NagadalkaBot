import re
import random
import requests
from typing import Callable
from bs4 import BeautifulSoup


class GreetingService:
	def __init__(self):
		self._greetings: list[str] = []

	def __call__(self, url: str):
		ENCODING = "windows-1251"

		request = requests.get(url)
		request.encoding = ENCODING
		soup = BeautifulSoup(request.text, 'lxml')

		def wrapper(callback: Callable[[BeautifulSoup], list[str]]):
			self._greetings += callback(soup)

		regex_pattern = r"{(\d+)-(\d+)}"
		if re.search(regex_pattern, url):
			limits = re.findall(regex_pattern, url)[0]
			def wrapper(callback: Callable[[BeautifulSoup], list[str]]):
				for page in range(*[int(x) for x in limits], 1):
					page_url = re.sub(regex_pattern, str(page), url)
					request = requests.get(page_url)
					request.encoding = ENCODING
					soup = BeautifulSoup(request.text, 'lxml')

					self._greetings += callback(soup)
			return wrapper

		return wrapper

	@property
	def get_random_greeting(self) -> str:
		return random.choice(self._greetings)
