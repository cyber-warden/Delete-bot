import os
import re
from urllib.parse import urlparse
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import (
    FloodWait, 
    ChatAdminRequired, 
    UsernameInvalid, 
    PeerIdInvalid,
    InviteHashExpired,
    UserAlreadyParticipant,
    MessageIdInvalid
)
import asyncio

# Configuration
API_ID = 23883349  # Replace with your API ID
API_HASH = "9ae2939989ed439ab91419d66b61a4a4"  # Replace with your API Hash
BOT_TOKEN = "7178702548:AAHSZ4DGLG1tv07WbyofBLoBEgwaxUKdj2A"  # Replace with your bot token
ADMIN_ID = 5429071679  # Replace with your Telegram admin ID

# User Configuration
SESSION_STRING = "BQFsblUATJX07DSP4x-GHRCV5iCqW2q8IB1VygaNJDSmZRTKollLBIG6FoW7WdKUGSa6SH-49lNpWRQZIqTvwPkZW1XtdXjGh7e3-Tihb3Tmvu_-V-ZfEVzB0Rrx_P_T0p5x-ahJb0AlL2_wY0J2ygUkJpPU2i_trsOQ3rhkjSWCfCmhAjoyBjTt4KWi500EoLZc2bmaGhLTzE_Ga4fPJ6glEaBrF-WMxfcsJi8GH_pIZFnQ9bKViaGaOR8gv8qGAH14K7YcUKeRHT_5_Ri6dZ0Zup1gmRv5X0K0lOxccuABYgw9pbazw3ZUpXmjJAMk89hcLQJlvET3UKO3pcazJt-MQglBOAAAAAFDmQ8_AA"  # Replace with your user session string

# Initialize Clients
# Initialize both bot and userbot
bot = Client(
    "delete_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user = Client(
    "user_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

async def extract_chat_info(url: str) -> tuple:
    """Extract chat username/id and message id from message link"""
    try:
        parts = url.split('/')
        chat_part = parts[-2]
        msg_id = int(parts[-1])
        
        if chat_part.startswith('+'):
            # Private channel invite link
            chat = await user.join_chat(chat_part[1:])
            chat_id = chat.id
        else:
            # Public channel username
            chat = await user.get_chat(chat_part)
            chat_id = chat.id
            
        return chat_id, msg_id
    except Exception as e:
        raise Exception(f"Failed to extract chat info: {str(e)}")

async def verify_permissions(chat_id):
    """Verify both bot and user have required permissions"""
    try:
        bot_member = await bot.get_chat_member(chat_id, "me")
        user_member = await user.get_chat_member(chat_id, "me")
        
        if not bot_member.privileges.can_delete_messages:
            raise ChatAdminRequired("Bot needs delete messages permission")
        if not user_member.privileges.can_delete_messages:
            raise ChatAdminRequired("Userbot needs delete messages permission")
            
    except Exception as e:
        raise Exception(f"Permission verification failed: {str(e)}")

async def analyze_messages_in_range(chat_id: int, start_id: int, end_id: int) -> tuple:
    """Analyze messages in the given range"""
    messages = []
    files = 0
    videos = 0
    texts = 0
    
    try:
        for msg_id in range(start_id, end_id + 1):
            try:
                msg = await user.get_messages(chat_id, msg_id)
                if msg and not msg.empty:
                    messages.append(msg)
                    if msg.document:
                        files += 1
                    elif msg.video:
                        videos += 1
                    elif msg.text:
                        texts += 1
            except MessageIdInvalid:
                continue
            except FloodWait as e:
                await asyncio.sleep(e.value)
    except Exception as e:
        raise Exception(f"Failed to analyze messages: {str(e)}")
        
    return messages, texts, files, videos

async def delete_messages_with_progress(messages: list, progress_message: Message) -> int:
    """Delete messages with progress updates"""
    total = len(messages)
    deleted = 0
    
    for i, message in enumerate(messages, 1):
        try:
            await user.delete_messages(message.chat.id, message.id)
            deleted += 1
            
            if i % 5 == 0 or i == total:  # Update progress every 5 messages
                await progress_message.edit_text(
                    f"<b>🗑 Deleting Messages...</b>\n\n"
                    f"<b>Progress:</b> {i}/{total} ({round((i/total)*100)}%)"
                )
                
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Error deleting message {message.id}: {str(e)}")
            
    return deleted

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text(
        "<b>🤖 Welcome to Advanced Delete Bot!</b>\n\n"
        "<b>Available Commands:</b>\n\n"
        "1️⃣ <code>/delete</code> <channel_link/username> <keyword>\n"
        "   - Deletes messages containing specific keyword\n"
        "   Example: <code>/delete @mychannel test</code>\n\n"
        "2️⃣ <code>/range</code> <start_msg_link> <end_msg_link>\n"
        "   - Deletes messages within specified range\n"
        "   Example: <code>/range https://t.me/channel/100 https://t.me/channel/200</code>\n\n"
        "<b>Note:</b> Bot requires admin rights with delete permission in the channel.\n"
        "Made with ❤️ by @YourUsername"
    )

@bot.on_message(filters.command("range") & filters.user(ADMIN_ID))
async def range_command(client, message):
    try:
        # Check command format
        if len(message.text.split()) != 3:
            await message.reply_text(
                "❌ <b>Invalid Format!</b>\n\n"
                "<b>Use:</b> <code>/range start_msg_link end_msg_link</code>\n"
                "<b>Example:</b> <code>/range https://t.me/channel/100 https://t.me/channel/200</code>"
            )
            return

        # Show processing message
        status_message = await message.reply_text(
            "<b>🔄 Processing Request...</b>"
        )

        try:
            # Extract chat and message IDs
            _, start_link, end_link = message.text.split()
            start_chat_id, start_msg_id = await extract_chat_info(start_link)
            end_chat_id, end_msg_id = await extract_chat_info(end_link)

            if start_chat_id != end_chat_id:
                raise Exception("Both messages must be from the same channel!")

            if start_msg_id > end_msg_id:
                start_msg_id, end_msg_id = end_msg_id, start_msg_id

            # Verify permissions
            await verify_permissions(start_chat_id)

            # Analyze messages
            await status_message.edit_text(
                "<b>🔍 Analyzing Messages in Range...</b>"
            )

            messages, texts, files, videos = await analyze_messages_in_range(
                start_chat_id, start_msg_id, end_msg_id
            )

            total_msgs = len(messages)
            if total_msgs == 0:
                await status_message.edit_text(
                    "❌ <b>No Messages Found in This Range!</b>"
                )
                return

            # Create confirmation message
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ DELETE", callback_data=f"range_{start_chat_id}_{start_msg_id}_{end_msg_id}"),
                    InlineKeyboardButton("❌ CANCEL", callback_data="cancel")
                ]
            ])

            await status_message.edit_text(
                "<b>📊 Range Analysis Report:</b>\n\n"
                f"<b>Message Range:</b> {start_msg_id} - {end_msg_id}\n"
                f"<b>Total Messages:</b> {total_msgs}\n\n"
                f"<b>Breakdown:</b>\n"
                f"📝 Text Messages: {texts}\n"
                f"📁 Files/Documents: {files}\n"
                f"🎥 Videos: {videos}\n\n"
                "<b>Would you like to proceed with deletion?</b>",
                reply_markup=keyboard
            )

        except Exception as e:
            await status_message.edit_text(
                f"❌ <b>Error:</b> {str(e)}"
            )

    except Exception as e:
        await message.reply_text(
            f"❌ <b>Error:</b> {str(e)}"
        )

# Update callback handler to handle range deletion
@bot.on_callback_query()
async def handle_callback(client, callback_query):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer(
            "⚠️ You're not authorized to perform this action.",
            show_alert=True
        )
        return

    if callback_query.data == "cancel":
        await callback_query.message.edit_text(
            "✅ <b>Task Cancelled!</b>"
        )
        return

    try:
        if callback_query.data.startswith("range_"):
            # Handle range deletion
            _, chat_id, start_id, end_id = callback_query.data.split("_")
            chat_id, start_id, end_id = int(chat_id), int(start_id), int(end_id)

            progress_msg = await callback_query.message.edit_text(
                "<b>🔍 Preparing to Delete Messages...</b>"
            )

            messages, _, _, _ = await analyze_messages_in_range(
                chat_id, start_id, end_id
            )

            deleted = await delete_messages_with_progress(
                messages, progress_msg
            )

            await progress_msg.edit_text(
                "✅ <b>Task Completed!</b>\n\n"
                f"<b>Successfully Deleted:</b> {deleted} messages\n"
                f"<b>From Range:</b> {start_id} - {end_id}"
            )

        # Keep existing delete command handling
        elif callback_query.data.startswith("delete_"):
            # Your existing delete command handling code here
            pass

    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ <b>Error:</b> {str(e)}"
        )

if __name__ == "__main__":
    user.start()
    bot.run()
