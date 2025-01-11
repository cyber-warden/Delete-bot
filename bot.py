import os
import re
from urllib.parse import urlparse
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    FloodWait, 
    ChatAdminRequired, 
    UsernameInvalid, 
    PeerIdInvalid,
    InviteHashExpired,
    UserAlreadyParticipant
)
import asyncio

# Configuration
API_ID = 23883349  # Replace with your API ID
API_HASH = "9ae2939989ed439ab91419d66b61a4a4"  # Replace with your API Hash
BOT_TOKEN = "7178702548:AAHSZ4DGLG1tv07WbyofBLoBEgwaxUKdj2A"  # Replace with your bot token
ADMIN_ID = 5429071679  # Replace with your Telegram admin ID

# User Configuration
USER_SESSION_STRING = "BQFsblUATJX07DSP4x-GHRCV5iCqW2q8IB1VygaNJDSmZRTKollLBIG6FoW7WdKUGSa6SH-49lNpWRQZIqTvwPkZW1XtdXjGh7e3-Tihb3Tmvu_-V-ZfEVzB0Rrx_P_T0p5x-ahJb0AlL2_wY0J2ygUkJpPU2i_trsOQ3rhkjSWCfCmhAjoyBjTt4KWi500EoLZc2bmaGhLTzE_Ga4fPJ6glEaBrF-WMxfcsJi8GH_pIZFnQ9bKViaGaOR8gv8qGAH14K7YcUKeRHT_5_Ri6dZ0Zup1gmRv5X0K0lOxccuABYgw9pbazw3ZUpXmjJAMk89hcLQJlvET3UKO3pcazJt-MQglBOAAAAAFDmQ8_AA"  # Replace with your user session string

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

async def extract_chat_id(client, chat_identifier):
    """Extract chat ID from various formats of chat identifiers"""
    try:
        # Check if it's an invite link
        if "t.me/" in chat_identifier:
            parsed = urlparse(chat_identifier)
            path = parsed.path.strip('/') if parsed.path else ''
            if parsed.path.startswith('/+'):
                # Handle private invite links
                invite_hash = path.replace('+', '')
                try:
                    chat = await user.join_chat(invite_hash)
                    return chat.id
                except UserAlreadyParticipant:
                    chat = await user.get_chat(invite_hash)
                    return chat.id
            else:
                # Handle public usernames
                chat = await client.get_chat(path)
                return chat.id
        else:
            # Handle direct chat IDs
            chat = await client.get_chat(chat_identifier)
            return chat.id
    except Exception as e:
        raise Exception(f"Failed to extract chat ID: {str(e)}")

async def verify_permissions(client, chat_id):
    """Verify both bot and user have required permissions"""
    try:
        bot_member = await bot.get_chat_member(chat_id, "me")
        user_member = await user.get_chat_member(chat_id, "me")
        
        bot_admin = bot_member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
        user_admin = user_member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
        
        if not bot_admin:
            raise ChatAdminRequired("Bot needs admin rights")
        if not user_admin:
            raise ChatAdminRequired("Userbot needs admin rights")
            
        required_permissions = ["can_delete_messages"]
        missing_permissions = [
            perm for perm in required_permissions 
            if not getattr(bot_member.privileges, perm, False)
        ]
        
        if missing_permissions:
            raise ChatAdminRequired(
                f"Bot missing required permissions: {', '.join(missing_permissions)}"
            )
            
    except Exception as e:
        raise Exception(f"Permission verification failed: {str(e)}")

async def search_messages(client, chat_id, keyword):
    """Search for messages containing the keyword"""
    messages = []
    files = []
    videos = []
    pattern = re.compile(keyword, re.IGNORECASE)
    
    try:
        async for message in client.search_messages(chat_id):
            try:
                if message.text and pattern.search(message.text):
                    messages.append(message)
                elif message.document and pattern.search(message.document.file_name):
                    files.append(message)
                elif message.video and pattern.search(message.video.file_name):
                    videos.append(message)
            except Exception:
                continue
    except Exception as e:
        raise Exception(f"Search failed: {str(e)}")
        
    return messages, files, videos

async def delete_messages_with_progress(client, messages, progress_message):
    """Delete messages with progress updates"""
    total = len(messages)
    deleted = 0
    
    for i, message in enumerate(messages, 1):
        try:
            await client.delete_messages(message.chat.id, message.id)
            deleted += 1
            
            if i % 10 == 0:  # Update progress every 10 messages
                await progress_message.edit_text(
                    f"Deleting messages: {i}/{total} completed..."
                )
                
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Error deleting message {message.id}: {str(e)}")
            
    return deleted

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text(
        "Welcome! I can delete messages, files, and videos from channels based on keywords.\n\n"
        "Use: /delete <channel_link/username/id> <keyword>\n"
        "Example: /delete @mychannel test"
    )

@bot.on_message(filters.command("delete") & filters.user(ADMIN_ID))
async def delete_command(client, message):
    try:
        # Check command format
        if len(message.text.split()) != 3:
            await message.reply_text(
                "❌ Invalid format!\n"
                "Use: /delete <channel_link/username/id> <keyword>"
            )
            return

        _, chat_identifier, keyword = message.text.split()
        
        # Show processing message
        status_message = await message.reply_text("🔄 Processing request...")
        
        try:
            # Extract chat ID and verify permissions
            chat_id = await extract_chat_id(user, chat_identifier)
            await verify_permissions(user, chat_id)
            
            # Search for messages
            await status_message.edit_text("🔍 Searching for messages...")
            messages, files, videos = await search_messages(user, chat_id, keyword)
            
            total_count = len(messages) + len(files) + len(videos)
            
            if total_count == 0:
                await status_message.edit_text("❌ No matching messages found.")
                return
                
            # Create confirmation message with inline keyboard
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ DELETE", callback_data=f"delete_{chat_id}_{keyword}"),
                    InlineKeyboardButton("❌ CANCEL", callback_data="cancel")
                ]
            ])
            
            await status_message.edit_text(
                f"📊 Found:\n"
                f"- {len(messages)} messages\n"
                f"- {len(files)} files\n"
                f"- {len(videos)} videos\n\n"
                f"Matching keyword: '{keyword}'\n"
                f"What would you like to do?",
                reply_markup=keyboard
            )
            
        except Exception as e:
            await status_message.edit_text(f"❌ Error: {str(e)}")
            
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@bot.on_callback_query()
async def handle_callback(client, callback_query):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer(
            "⚠️ You're not authorized to perform this action.",
            show_alert=True
        )
        return

    if callback_query.data == "cancel":
        await callback_query.message.edit_text("✅ Task cancelled.")
        return

    if callback_query.data.startswith("delete_"):
        try:
            _, chat_id, keyword = callback_query.data.split("_")
            chat_id = int(chat_id)
            
            # Search messages again to ensure fresh results
            progress_msg = await callback_query.message.edit_text(
                "🔍 Searching messages..."
            )
            
            messages, files, videos = await search_messages(user, chat_id, keyword)
            
            # Delete messages with progress updates
            await progress_msg.edit_text("🗑 Deleting messages...")
            
            msgs_deleted = await delete_messages_with_progress(
                user, messages, progress_msg
            )
            files_deleted = await delete_messages_with_progress(
                user, files, progress_msg
            )
            videos_deleted = await delete_messages_with_progress(
                user, videos, progress_msg
            )
            
            summary = (
                "✅ Task Completed!\n\n"
                "📊 Summary:\n"
                f"- Messages Deleted: {msgs_deleted}\n"
                f"- Files Deleted: {files_deleted}\n"
                f"- Videos Deleted: {videos_deleted}"
            )
            
            await progress_msg.edit_text(summary)
            
        except Exception as e:
            await callback_query.message.edit_text(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    user.start()
    bot.run()
