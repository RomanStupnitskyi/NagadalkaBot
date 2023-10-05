import ast
from datetime import datetime
from pymongo import MongoClient
from .middlewares.IsOwner import IsOwnerMiddleware

from aiogram import Router
from aiogram.types import Message
from aiogram.filters.command import Command


development_router = Router(name="development")
development_router.message.middleware(IsOwnerMiddleware())


def insert_returns(body):
	if isinstance(body[-1], ast.Expr):
		body[-1] = ast.Return(body[-1].value)
		ast.fix_missing_locations(body[-1])

	if isinstance(body[-1], ast.If):
		insert_returns(body[-1].body)
		insert_returns(body[-1].orelse)

	if isinstance(body[-1], ast.With):
		insert_returns(body[-1].body)


@development_router.message(Command("eval"))
async def evaluate(message: Message, db: MongoClient) -> None:
	try:
		fn_name = "_eval_expr"
		cmd = message.text.split(" ")
		cmd.pop(0)
		cmd = " ".join(cmd)

		cmd = "\n".join(f"    {i}" for i in cmd.splitlines())
		body = f"async def {fn_name}():\n{cmd}"

		parsed = ast.parse(body)
		body = parsed.body[0].body

		insert_returns(body)

		env = {
			'message': message,
			'bot': message.bot,
			'db': db,
			'__import__': __import__
		}
		exec(compile(parsed, filename="<ast>", mode="exec"), env)

		start = datetime.now().timestamp()
		result = (await eval(f"{fn_name}()", env))
		end = datetime.now().timestamp()
		
		await message.reply("Successfully done in {0} ms.\n\nResult:\n<pre language='python'>{1}</pre>".format(round(end - start, 2), result, 10))
	except Exception as error:
		await message.reply("Finished with an error:\n<pre>{0}</pre>".format(error))


@development_router.message(Command("reset"))
async def reset_command(message: Message, db: MongoClient) -> None:
	user_data = { 'id': message.from_user.id }

	if message.reply_to_message and not message.reply_to_message.from_user.is_bot:
		user_data = { 'id': message.reply_to_message.from_user.id }
		db.user.data.delete_one(user_data)
		db.user.data.insert_one(user_data)

		await message.reply("✅ User's data has been reset")
		return None
	
	db.user.data.delete_one(user_data)
	db.user.data.insert_one(user_data)

	await message.reply("✅ Data has been reset")


@development_router.message(Command("user_id"))
async def user_id_command(message: Message) -> None:
	await message.reply(
		"User id: <code>{0}</code>"
			.format(
				message.reply_to_message.from_user.id
					if message.reply_to_message and not message.reply_to_message.from_user.is_bot
					else message.from_user.id
				)
		)


@development_router.message(Command("set_group"))
async def set_group(message: Message, db: MongoClient) -> None:
	if message.chat.type == 'group' or message.chat.type == 'supergroup':
		db.telegram.config.update_one(
			{ 'owner_id': str(message.from_user.id) },
			{ '$set': { 'group_id': message.chat.id } }
		)
		await message.reply('✅ Group updated')
	else:
		await message.reply('❌ Current chat is not a group')
