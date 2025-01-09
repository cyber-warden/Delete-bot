from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Configuration
API_ID = 23883349  # Replace with your API ID
API_HASH = "9ae2939989ed439ab91419d66b61a4a4"  # Replace with your API Hash
BOT_TOKEN = "7178702548:AAHSZ4DGLG1tv07WbyofBLoBEgwaxUKdj2A"  # Replace with your bot token
ADMIN_ID = 5429071679  # Replace with your Telegram admin ID
SESSION_STRING = "BQFsblUATJX07DSP4x-GHRCV5iCqW2q8IB1VygaNJDSmZRTKollLBIG6FoW7WdKUGSa6SH-49lNpWRQZIqTvwPkZW1XtdXjGh7e3-Tihb3Tmvu_-V-ZfEVzB0Rrx_P_T0p5x-ahJb0AlL2_wY0J2ygUkJpPU2i_trsOQ3rhkjSWCfCmhAjoyBjTt4KWi500EoLZc2bmaGhLTzE_Ga4fPJ6glEaBrF-WMxfcsJi8GH_pIZFnQ9bKViaGaOR8gv8qGAH14K7YcUKeRHT_5_Ri6dZ0Zup1gmRv5X0K0lOxccuABYgw9pbazw3ZUpXmjJAMk89hcLQJlvET3UKO3pcazJt-MQglBOAAAAAFDmQ8_AA"  # Replace with your session string

bot = Client("deleteBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Start command
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Hello Admin! Use /delete command to manage messages.")
    else:
        await message.reply("You are not authorized to use this bot.")

# Delete command
@bot.on_message(filters.command("delete") & filters.private)
async def delete_command(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("You are not authorized to use this command.")
        return

    try:
        command = message.text.split(" ", 2)
        if len(command) < 3:
            await message.reply("Invalid format! Use:\n`/delete chat_id keyword`")
            return

        chat_id = command[1]
        keyword = command[2]

        async for msg in client.search_messages(chat_id, query=keyword):
            if msg:
                await message.reply(
                    f"Found message with keyword: **{keyword}**\n\nDo you want to delete it?",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("DELETE", callback_data=f"delete:{chat_id}:{keyword}"),
                                InlineKeyboardButton("CANCEL", callback_data="cancel"),
                            ]
                        ]
                    ),
                )
                return

        await message.reply(f"No messages found with the keyword: **{keyword}**.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# Callback handler
@bot.on_callback_query()
async def handle_callback_query(client, callback_query: CallbackQuery):
    data = callback_query.data

    if data.startswith("delete:"):
        _, chat_id, keyword = data.split(":", 2)

        deleted_count = {"messages": 0, "files": 0, "videos": 0}
        async for msg in client.search_messages(chat_id, query=keyword):
            try:
                if msg.video:
                    deleted_count["videos"] += 1
                elif msg.document:
                    deleted_count["files"] += 1
                else:
                    deleted_count["messages"] += 1
                await msg.delete()
            except Exception as e:
                print(f"Failed to delete message: {e}")

        await callback_query.message.edit_text(
            f"Task done!\n\n**Summary:**\n"
            f"Messages deleted: {deleted_count['messages']}\n"
            f"Files deleted: {deleted_count['files']}\n"
            f"Videos deleted: {deleted_count['videos']}"
        )
    elif data == "cancel":
        await callback_query.message.edit_text("Operation canceled.")

# Run the bot
bot.run()
