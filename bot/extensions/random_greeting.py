from bs4 import BeautifulSoup

from .abstracts.GreetingService import GreetingService


greeting_service = GreetingService()


@greeting_service("https://pozdravok.com/pozdravleniya/den-rozhdeniya/i/na-ukrainskom/korotki")
def pozdravok_greetings(soup: BeautifulSoup) -> list[str]:
	return [a.decode_contents().replace("<br/>", "\n") for a in soup.find_all("p")]

@greeting_service("https://pozdravok.com/pozdravleniya/den-rozhdeniya/i/na-ukrainskom/korotki/{2-11}.htm")
def pozdravok_greetings(soup: BeautifulSoup) -> list[str]:
	return [a.decode_contents().replace("<br/>", "\n") for a in soup.find_all("p")]
