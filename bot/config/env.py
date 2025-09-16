from decouple import config

BOT_TOKEN = config("BOT_TOKEN")
BASE_URL = config("BASE_URL")

print("BASE_URL", BASE_URL)