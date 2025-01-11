import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, ChatAdminRequired, UsernameInvalid, PeerIdInvalid
import asyncio

# Configuration
API_ID = 23883349  # Replace with your API ID
API_HASH = "9ae2939989ed439ab91419d66b61a4a4"  # Replace with your API Hash
BOT_TOKEN = "7178702548:AAHSZ4DGLG1tv07WbyofBLoBEgwaxUKdj2A"  # Replace with your bot token
ADMIN_ID = 5429071679  # Replace with your Telegram admin ID

# User Configuration
USER_SESSION_STRING = "BQFsblUATJX07DSP4x-GHRCV5iCqW2q8IB1VygaNJDSmZRTKollLBIG6FoW7WdKUGSa6SH-49lNpWRQZIqTvwPkZW1XtdXjGh7e3-Tihb3Tmvu_-V-ZfEVzB0Rrx_P_T0p5x-ahJb0AlL2_wY0J2ygUkJpPU2i_trsOQ3rhkjSWCfCmhAjoyBjTt4KWi500EoLZc2bmaGhLTzE_Ga4fPJ6glEaBrF-WMxfcsJi8GH_pIZFnQ9bKViaGaOR8gv8qGAH14K7YcUKeRHT_5_Ri6dZ0Zup1gmRv5X0K0lOxccuABYgw9pbazw3ZUpXmjJAMk89hcLQJlvET3UKO3pcazJt-MQglBOAAAAAFDmQ8_AA"  # Replace with your user session string


# Initialize the bot
bot = Client("delete_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize userbot if SESSION_STRING is provided
userbot = None
if SESSION_STRING:
    userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

async def is_admin(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["creator", "administrator"]
    except Exception:
        return False

async def search_messages(client, chat_id, keyword):
    messages = []
    files = []
    videos = []
    async for message in client.get_chat_history(chat_id):
        if keyword.lower() in message.text.lower() if message.text else False:
            messages.append(message)
        elif message.document and keyword.lower() in message.document.file_name.lower():
            files.append(message)
        elif message.video and keyword.lower() in message.video.file_name.lower():
            videos.append(message)
    return messages, files, videos

async def delete_messages(client, messages):
    deleted_count = 0
    for message in messages:
        try:
            await client.delete_messages(message.chat.id, message.id)
            deleted_count += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Error deleting message: {e}")
    return deleted_count

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text(
        "Welcome! I'm a bot that can delete messages, files, and videos from a channel based on a keyword.\n\n"
        "Use the /delete command to start the deletion process.\n"
        "Format: /delete <channel_link/username/chat_id> <keyword>"
    )

@bot.on_message(filters.command("delete") & filters.user(ADMIN_ID))
async def delete_command(client, message):
    # Check if the command format is correct
    if len(message.text.split()) != 3:
        await message.reply_text("Invalid format. Use: /delete <channel_link/username/chat_id> <keyword>")
        return

    _, chat_id, keyword = message.text.split()

    try:
        # Try to get the chat
        chat = await bot.get_chat(chat_id)
        
        # Check if the bot is an admin in the chat
        if not await is_admin(chat.id, (await bot.get_me()).id):
            await message.reply_text("I need to be an admin in the channel to perform this action.")
            return

        # Use userbot if available, otherwise use bot
        client_to_use = userbot if userbot else bot

        # Search for messages
        messages, files, videos = await search_messages(client_to_use, chat.id, keyword)

        total_count = len(messages) + len(files) + len(videos)

        if total_count == 0:
            await message.reply_text("No matching messages found.")
            return

        # Create inline keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("DELETE", callback_data=f"delete_{chat.id}_{keyword}"),
             InlineKeyboardButton("CANCEL", callback_data="cancel")]
        ])

        await message.reply_text(
            f"Found {len(messages)} messages, {len(files)} files, and {len(videos)} videos matching the keyword '{keyword}'.\n"
            "What would you like to do?",
            reply_markup=keyboard
        )

    except (UsernameInvalid, PeerIdInvalid):
        await message.reply_text("Invalid channel link/username/chat_id. Please check and try again.")
    except ChatAdminRequired:
        await message.reply_text("I need to be an admin in the channel to perform this action.")
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")

@bot.on_callback_query()
async def handle_callback(client, callback_query):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("You're not authorized to perform this action.", show_alert=True)
        return

    if callback_query.data == "cancel":
        await callback_query.message.edit_text("Task cancelled.")
        return

    if callback_query.data.startswith("delete_"):
        _, chat_id, keyword = callback_query.data.split("_")
        chat_id = int(chat_id)

        client_to_use = userbot if userbot else bot

        messages, files, videos = await search_messages(client_to_use, chat_id, keyword)

        messages_deleted = await delete_messages(client_to_use, messages)
        files_deleted = await delete_messages(client_to_use, files)
        videos_deleted = await delete_messages(client_to_use, videos)

        summary = (
            "Task Completed!\n"
            "Summary:\n"
            f"- Messages Deleted: {messages_deleted}\n"
            f"- Files Deleted: {files_deleted}\n"
            f"- Videos Deleted: {videos_deleted}"
        )

        await callback_query.message.edit_text(summary)

if __name__ == "__main__":
    if userbot:
        userbot.start()
    bot.run()
