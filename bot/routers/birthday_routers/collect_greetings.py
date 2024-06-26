import re
from aiogram import Router
from pymongo import MongoClient

from aiogram.types.callback_query import CallbackQuery

from bot.filters.IsButton import IsButton


greet_router = Router(name='greet')


@greet_router.callback_query(IsButton('greet_button'))
async def greet_button(callback: CallbackQuery, database_client: MongoClient):
	collection = database_client.user.birthdays
	message = callback.message

	user_id = int(re.search(r"tg://user\?id=(\d+)", message.html_text).group(1))
	greeting = collection.find_one({
		"user_id": user_id,
		"group_id": message.chat.id,
		"message_id": message.message_id })
	
	if not greeting:
		return await callback.answer("⌛️ Час для привітань минув", show_alert=True)
	
	callback_user_id = callback.from_user.id
	
	if user_id == callback_user_id:
		return await callback.answer("Приєднуюсь до твоїх привітань 😘", show_alert=True)

	if callback_user_id in greeting["greeted_by"]:
		return await callback.answer("🫶 Твоє привітання вже збережено", show_alert=True)
	
	collection.update_one(
		{ "user_id": user_id, "group_id": message.chat.id, "message_id": message.message_id },
		{ "$addToSet": { "greeted_by": callback_user_id } })
	
	greetings_amount = int(re.search(r"<code>(\d+)</code>", message.html_text).group(1))
	await message.edit_text(re.sub(r"<code>(\d+)</code>", f"<code>{greetings_amount+1}</code>", message.html_text), reply_markup=message.reply_markup)
	return await callback.answer("Дякую за привітання ;)", show_alert=True)


@greet_router.callback_query(IsButton("who_greeted_button"))
async def who_greeted_button(callback: CallbackQuery, database_client: MongoClient):
	message = callback.message
	user_id = int(re.search(r"tg://user\?id=(\d+)", message.html_text).group(1))

	greeting = database_client.user.birthdays.find_one({
		"user_id": user_id,
		"group_id": message.chat.id,
		"message_id": message.message_id })
	if not greeting:
		return await callback.answer("⌛️ Список привітань доступний тільки протягом дня народження", show_alert=True)

	greeted_by = ", ".join(
		[
			(await message.chat.get_member(user_id)).user.full_name
			for user_id in greeting["greeted_by"]
		]) or "тільки від мене 💋"
	callback_answer = f"👥 Отримано привітання від:\n\n{greeted_by}"
	return await callback.answer(callback_answer if len(callback_answer) < 200 else callback_answer[:197] + "...", show_alert=True)
