import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, ChatMemberUpdated
from aiogram.exceptions import TelegramBadRequest

# 1. ВСТАВТЕ СВІЙ ТОКЕН ВІД BOTFATHER ЗАМІСТЬ "ВАШ_BOT_TOKEN_ТУТ"
BOT_TOKEN = "8617221494:AAES1IFswmcktq6qy3-3lTt7kI5C1A6kP8o"

# 2. ВСТАВТЕ ID ВАШОГО КАНАЛУ ТА ЧАТУ (починаються з -100)
CHANNEL_ID = "@banlab_community" # ID телеграм-каналу
CHAT_ID = -1004361320220     # ID телеграм-чату

# 3. ВСТАВТЕ ПОСИЛАННЯ НА ВАШ КАНАЛ
CHANNEL_LINK = "https://t.me/banlab_community" 

from aiogram.client.session.aiohttp import AiohttpSession

session = AiohttpSession(proxy="http://proxy.server:3128")
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# Права: обмеження можливості писати (заборона писати)
NO_RIGHTS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False
)

# Повні права на відправку повідомлень (дозвіл писати)
FULL_RIGHTS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True
)

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        print(f"Статус користувача {user_id}: {member.status}")
        
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except Exception as e:
        print(f"Помилка Telegram API: {e}")
        return False

# 1. Команда /start у приватних повідомленнях з ботом
@dp.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: types.Message):
    is_subscribed = await check_subscription(message.from_user.id)
    
    if is_subscribed:
        chat_invite = await bot.create_chat_invite_link(chat_id=CHAT_ID, member_limit=1)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Приєднатися до чату 💬", url=chat_invite.invite_link)]
        ])
        await message.answer("Дякуємо за підписку! Ось твоє одноразове посилання на чат:", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Підписатися на канал 📢", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="Я підписався ✅", callback_data="check_sub")]
        ])
        await message.answer("Щоб отримати доступ до чату, підпишіться на наш канал:", reply_markup=kb)

# Перевірка підписки після натискання кнопки "Я підписався"
@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    is_subscribed = await check_subscription(callback.from_user.id)
    
    if is_subscribed:
        chat_invite = await bot.create_chat_invite_link(chat_id=CHAT_ID, member_limit=1)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Приєднатися до чату 💬", url=chat_invite.invite_link)]
        ])
        await callback.message.edit_text("Чудово! Доступ відкрито:", reply_markup=kb)
    else:
        try:
    await callback.answer("Ви все ще не підписалися на канал!", show_alert=True)
except TelegramBadRequest:
    pass

# 2. Відстеження дій у КАНАЛІ (відписка / підписка назад)
@dp.chat_member(F.chat.id == CHANNEL_ID)
async def on_channel_member_update(event: ChatMemberUpdated):
    user_id = event.from_user.id
    new_status = event.new_chat_member.status

    try:
        chat_member = await bot.get_chat_member(chat_id=CHAT_ID, user_id=user_id)
        if chat_member.status in ["left", "kicked"]:
            return
    except Exception:
        return

    # Відписався від каналу -> блокуємо право писати в чаті
    if new_status in ["left", "kicked"]:
        await bot.restrict_chat_member(
            chat_id=CHAT_ID,
            user_id=user_id,
            permissions=NO_RIGHTS
        )
        logging.info(f"Користувача {user_id} обмежено в чаті через відписку.")

    # Підписався назад -> повертаємо право писати в чаті
    elif new_status in ["member", "administrator", "creator"]:
        await bot.restrict_chat_member(
            chat_id=CHAT_ID,
            user_id=user_id,
            permissions=FULL_RIGHTS
        )
        logging.info(f"Користувачу {user_id} повернуто права в чаті.")

# 3. Перевірка при вході в ЧАТ
@dp.chat_member(F.chat.id == CHAT_ID, ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_user_join_chat(event: ChatMemberUpdated):
    user_id = event.from_user.id
    is_subscribed = await check_subscription(user_id)

    if not is_subscribed:
        await bot.restrict_chat_member(
            chat_id=CHAT_ID,
            user_id=user_id,
            permissions=NO_RIGHTS
        )

async def main():
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
