from pymongo import MongoClient

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.types.callback_query import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .filters.Group import Group
from .extensions.GetRandomWord import GetRandomWord


crocodile_router = Router(name="crocodile")


# =================================================================================
# /CROCODILE - crocodile game to guess the mystery word by explaining it to others
# =================================================================================


@crocodile_router.message(Command("crocodile"), Group())
async def crocodile_handler(message: Message, db: MongoClient) -> None:
	game = db.crocodile.games.find_one({ "chat_id": message.chat.id })
	if game:
		await message.reply("❗️ Гру вже розпочато")
		return None

	word: str = GetRandomWord().lower()

	db.crocodile.games.insert_one({
		"chat_id": message.chat.id,
		"word": word,
		"created_by": message.from_user.id
	})

	show_word_button = InlineKeyboardButton(
		text="Показати слово", callback_data="show_word"
	)
	change_word_button = InlineKeyboardButton(
		text="Змінити слово", callback_data="change_word"
	)
	markup = InlineKeyboardMarkup(inline_keyboard=[[show_word_button, change_word_button]])
	
	await message.reply(
		"🐊 Гру розпочато, <a href='tg://user?id={0}'>{1}</a> пояснює слово"
			.format(message.from_user.id, message.from_user.full_name),
		reply_markup=markup
	)


@crocodile_router.callback_query(F.data == "show_word")
async def show_word_handler(callback: CallbackQuery, db: MongoClient) -> None:
	game = db.crocodile.games.find_one({ "chat_id": callback.message.chat.id })

	if not game:
		await callback.answer("❗️ Гру вже закінчено", show_alert=True)
		return None
	
	if game["created_by"] != callback.from_user.id:
		await callback.answer("❗️ Ти не можеш подивитись слово, ти вгадуєш його", show_alert=True)
		return None

	await callback.answer("🐊 Твоє слово: {0}".format(game["word"]), show_alert=True)


@crocodile_router.callback_query(F.data == "change_word")
async def change_word_handler(callback: CallbackQuery, db: MongoClient) -> None:
	game = db.crocodile.games.find_one({ "chat_id": callback.message.chat.id })

	if not game:
		await callback.answer("❗️ Гру вже закінчено", show_alert=True)
		return None

	if game["created_by"] != callback.from_user.id:
		await callback.answer("❗️ Ти не можеш змінити слово, ти вгадуєш його", show_alert=True)
		return None

	word: str = GetRandomWord().lower()
	db.crocodile.games.update_one({ "chat_id": callback.message.chat.id }, { "$set": { "word": word } })
	await callback.answer("🐊 Твоє нове слово: {0}".format(word), show_alert=True)


@crocodile_router.message(Group())
async def crocodile_message_handler(message: Message, db: MongoClient) -> None:
	game = db.crocodile.games.find_one({ "chat_id": message.chat.id })
	if not game:
		return None

	if game["created_by"] == message.from_user.id and game["word"] in message.text.lower():
		await message.delete()
		return None

	if game["created_by"] != message.from_user.id and game["word"] == message.text.lower():
		db.crocodile.games.delete_one({ "chat_id": message.chat.id })

		await message.answer(
			"🎉 <a href='tg://user?id={0}'>{1}</a> вгадав слово, це було слово <b>{2}</b>"
				.format(message.from_user.id, message.from_user.full_name, game["word"])
		)
