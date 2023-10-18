import requests
from bs4 import BeautifulSoup


def GetRandomWord() -> str:
	"""
	Retrieves a random word from http://sum.in.ua/random and returns it as a string.

	Returns:
	- str: A random word from http://sum.in.ua/random.
	"""
	URL = 'http://sum.in.ua/random'
	request = requests.get(URL)
	soup = BeautifulSoup(request.text, 'lxml')
	word = soup.find('div', id="tlum").find('strong').getText()
	return word
