import sys
from dotenv import load_dotenv

from bot import Factory


if __name__ == "__main__":
	if not "--hosting" in sys.argv:
		load_dotenv()

	factory: Factory = Factory()
	factory.start()
