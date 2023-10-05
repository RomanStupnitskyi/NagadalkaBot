from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types.message import Message
from aiogram.filters.state import StateFilter
from aiogram.filters.command import Command


general_router = Router(name="general")


@general_router.message(Command("start"))
async def start_command(message: Message) -> None:
	await message.answer("Привіт! Я - Нагадалка, буду нагадувати коли у кого день народження і не тільки. Щоб вказати свій день народження, використовуй команду /birthday")


@general_router.message(Command("cencel"), StateFilter("*"))
async def cencel_command(message: Message, state: FSMContext) -> None:
	current_state = await state.get_state()
	if current_state is None:
		return

	await state.clear()
	await message.reply('Cancelled.')

@general_router.message(Command("id"))
async def id_command(message: Message) -> None:
	await message.reply('🔐 Your id: <code>{0}</code>'.format(message.from_user.id))
