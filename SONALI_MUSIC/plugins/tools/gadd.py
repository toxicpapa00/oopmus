import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import ChatAdminRequired, FloodWait, RPCError, PeerIdInvalid, UserNotParticipant
from SONALI_MUSIC import app
from SONALI_MUSIC.utils.database import get_assistant

# --- Filter Setup ---
OWNERS = [8238387029]
OWNER_FILTER = filters.user(OWNERS) # Define filter here
GLOBAL_CANCEL = False


@app.on_callback_query(filters.regex("cancel_add_bot") & OWNER_FILTER) # 1. Filter applied here
async def cancel_process(_, query):
    global GLOBAL_CANCEL

    # 2. Owner check is now handled by the filter, no need for manual check
    GLOBAL_CANCEL = True
    await query.answer("🚫 Process Cancel किया गया!", show_alert=True)
    await query.edit_message_reply_markup(None)


@app.on_message(filters.command("gadd") & OWNER_FILTER) # 1. Filter applied here
async def add_allbot(_, message: Message):
    global GLOBAL_CANCEL
    GLOBAL_CANCEL = False

    cmd = message.text.split()
    if len(cmd) != 2:
        return await message.reply("❌ Use: `/gadd bot_username`")

    bot_username = cmd[1]

    try:
        userbot = await get_assistant(message.chat.id)

        try:
            bot = await app.get_users(bot_username)
        except PeerIdInvalid:
            return await message.reply("❌ Bot Username गलत है!")

        bot_id = bot.id

        added = full = limited = failed = 0
        dialogs = [d async for d in userbot.get_dialogs()]

        if not dialogs:
            return await message.reply("⚠️ Assistant किसी भी चैट में नहीं है।")

        total = len(dialogs)

        msg = await message.reply(
            f"🔄 `{bot_username}` को सभी groups में add किया जा रहा है...\n\n📌 Total Chats: `{total}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⛔ Cancel", callback_data="cancel_add_bot")]
            ])
        )

        await userbot.send_message(bot_username, "/start")

        FULL_RIGHTS = {
            "can_change_info": True,
            "can_delete_messages": True,
            "can_restrict_members": True,
            "can_pin_messages": True,
            "can_invite_users": True,
            "can_promote_members": True,
        }

        for index, dialog in enumerate(dialogs):

            if GLOBAL_CANCEL:
                break

            chat_id = dialog.chat.id
            status = "Processing..."

            try:
                # 3. Improved adding/joining attempt
                try:
                    await userbot.add_chat_members(chat_id, bot_id)
                except UserNotParticipant:
                    pass # Bot is already in the chat, safe to continue
                except ChatAdminRequired:
                    # Assistant cannot add members to this chat
                    failed += 1
                    status = "Failed (Admin Required to Add) ❌"
                    continue # Skip to the next dialog

                # Get assistant's own member object
                me = await userbot.get_chat_member(chat_id, userbot.id)

                # Promotion Logic
                if me.status in ["administrator", "creator"]:

                    if me.can_promote_members:
                        await userbot.promote_chat_member(chat_id, bot_id, **FULL_RIGHTS)
                        full += 1
                        status = "Full Admin 👑"
                    else:
                        # Limited Rights Promotion
                        await userbot.promote_chat_member(
                            chat_id, bot_id,
                            can_change_info=me.can_change_info,
                            can_delete_messages=me.can_delete_messages,
                            can_restrict_members=me.can_restrict_members,
                            can_pin_messages=me.can_pin_messages,
                            can_invite_users=me.can_invite_users,
                            can_promote_members=False
                        )
                        limited += 1
                        status = "Limited Admin ⭐"
                else:
                    # Assistant is not admin, bot remains a regular member
                    added += 1
                    status = "Added Only ➕"

            # --- Specific Error Handling ---
            except FloodWait as e:
                await asyncio.sleep(e.value + 5) # Added buffer time
                continue 

            except ChatAdminRequired:
                failed += 1
                status = "Failed (Lost Admin Rights) ❌"
            
            except RPCError:
                failed += 1
                status = "Failed (RPC Error) ❌"
            
            except Exception:
                # Catch-all for any other unforeseen issues
                failed += 1
                status = "Failed (Unknown Error) ❌"

            # Update Progress Message
            progress = int(((index + 1) / total) * 100)

            await msg.edit(
                f"🚀 Progress: `{progress}%` ({index+1}/{total})\n\n"
                f"👑 Full Admin: `{full}`\n⭐ Limited: `{limited}`\n➕ Added: `{added}`\n❌ Failed: `{failed}`\n\n"
                f"📍 Last: {status}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⛔ Cancel", callback_data="cancel_add_bot")]
                ])
            )
            await asyncio.sleep(2)

        # Final Summary
        done_by = f"@{userbot.username}" if userbot.username else userbot.first_name

        await msg.edit(
            f"🎯 **Process {'Cancelled ❌' if GLOBAL_CANCEL else 'Completed 🎉'}**\n\n"
            f"👑 Full Admin: `{full}`\n⭐ Limited: `{limited}`\n➕ Added: `{added}`\n❌ Failed: `{failed}`\n\n"
            f"🧑‍💻 By: **{done_by}**",
            reply_markup=None # Remove button on completion/cancellation
        )

    except Exception as e:
        await message.reply(f"⚠️ **Major Error:**\n`{str(e)}`\n\nEnsure Assistant is running.")
      
