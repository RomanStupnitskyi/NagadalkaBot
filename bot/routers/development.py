import ast
from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection

from aiogram import Router
from aiogram.types import Message
from aiogram.filters.command import Command

from bot.middlewares.IsOwner import IsOwnerMiddleware


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
async def evaluate(message: Message, database_client: MongoClient) -> None:
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
			'database_client': database_client,
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
async def reset_command(message: Message, database_client: MongoClient) -> None:
	user_data = { 'id': message.from_user.id }
	collection: Collection = database_client.user.data

	reply_to_message = message.reply_to_message
	if reply_to_message and not reply_to_message.from_user.is_bot:
		user_data = { 'id': reply_to_message.from_user.id }
		collection.delete_one(user_data)

		return await message.reply("✅ User's data has been reset")
	
	collection.delete_one(user_data)

	return await message.reply("✅ Data has been reset")
