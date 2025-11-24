# app/handlers/handlers.py
import logging
from aiogram import Bot, Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import ADMIN_ID
from states import Form, Admin
from keyboards import join_kb, admin_kb
from utils import (
    ACCEPTED_USERS, pending_applications, user_photo_msg,
    is_subscribed, eternal_photo, delete_user_messages
)
import database as db

logger = logging.getLogger("GodBot")
router = Router()

# ====================== ХЕНДЛЕРЫ ======================
@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext, bot: Bot):
    await delete_user_messages(message, bot)

    # Админ не проходит анкету
    if message.from_user.id == ADMIN_ID:
        await message.answer("Ты админ, тебе не нужно проходить анкету")
        return

    if message.from_user.id in ACCEPTED_USERS and await is_subscribed(bot, message.from_user.id):
        await eternal_photo(message, bot, "ДОБРО ПОЖАЛОВАТЬ В ЗАКРЫТУЮ КОМАНДУ!\n\nТы в элите\nВесь профит — в закрытом чате\n\nДелай бабки, брат")
        return

    await eternal_photo(message, bot, f"Привет, <b>{message.from_user.first_name}</b>!\n\nПройди 4 вопроса, чтобы попасть в команду\n\n<b>1/4 → Твой ник в игре:</b>")
    await state.set_state(Form.nickname)

@router.message(Form.nickname)
async def process_nickname(message: types.Message, state: FSMContext, bot: Bot):
    await delete_user_messages(message, bot)
    await state.update_data(nickname=message.text.strip())
    await eternal_photo(message, bot, "Ник сохранён\n\n<b>2/4 → Был опыт в таких проектах?</b>\n(если нет — напиши <code>-</code>)")
    await state.set_state(Form.experience)

@router.message(Form.experience)
async def process_experience(message: types.Message, state: FSMContext, bot: Bot):
    await delete_user_messages(message, bot)
    exp = "Нет опыта" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(experience=exp)
    if message.text.strip() == "-":
        await state.update_data(duration="—")
        await ask_source(message, state, bot)
    else:
        await eternal_photo(message, bot, "Опыт сохранён\n\n<b>3/4 → Как долго ты в теме?</b>")
        await state.set_state(Form.duration)

@router.message(Form.duration)
async def process_duration(message: types.Message, state: FSMContext, bot: Bot):
    await delete_user_messages(message, bot)
    await state.update_data(duration=message.text.strip())
    await ask_source(message, state, bot)

async def ask_source(message: types.Message, state: FSMContext, bot: Bot):
    await delete_user_messages(message, bot)
    await eternal_photo(message, bot, "Стаж сохранён\n\n<b>4/4 → Откуда о нас узнал?</b>\n(друг, тикток, реклама, ютуб…)")
    await state.set_state(Form.source)

@router.message(Form.source)
async def process_source(message: types.Message, state: FSMContext, bot: Bot):
    await delete_user_messages(message, bot)
    await state.update_data(source=message.text.strip())
    data = await state.get_data()

    # Сохраняем в БД
    db.save_user_application(
        user_id=message.from_user.id,
        username=message.from_user.username or "—",
        full_name=message.from_user.full_name,
        nickname=data['nickname'],
        source=data['source'],
        experience=data['experience']
    )

    await eternal_photo(message, bot,
        f"ЗАЯВКА ОТПРАВЛЕНА!\n\n"
        f"• Ник: <b>{data['nickname']}</b>\n"
        f"• Опыт: <b>{data['experience']}</b>\n"
        f"• Стаж: <b>{data.get('duration', '—')}</b>\n"
        f"• Откуда узнал: <b>{data['source']}</b>\n\n"
        f"Жди ответа"
    )

    admin_text = (
        f"НОВАЯ ЗАЯВКА\n\n"
        f"Имя: {message.from_user.full_name}\n"
        f"ID: <code>{message.from_user.id}</code>\n"
        f"@{message.from_user.username or '—'}\n\n"
        f"Ник: {data['nickname']}\n"
        f"Опыт: {data['experience']}\n"
        f"Стаж: {data.get('duration', '—')}\n"
        f"Откуда узнал: {data['source']}"
    )

    sent = await bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb(message.from_user.id), parse_mode=ParseMode.HTML)
    
    pending_applications[message.from_user.id] = {
        "user_msg_id": user_photo_msg[message.from_user.id],
        "admin_msg_id": sent.message_id
    }
    await state.clear()

# ====================== АДМИН ======================
@router.callback_query(F.data.startswith(("acc_", "rej_")))
async def admin_action(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    action, uid = callback.data.split("_", 1)
    uid = int(uid)
    if uid not in pending_applications:
        return

    if action == "acc":
        ACCEPTED_USERS.add(uid)
        
        # Сохраняем одобрение в БД
        db.approve_user(uid, callback.from_user.id)
        
        await callback.message.edit_text("✅ ЗАЯВКА ПРИНЯТА", parse_mode=ParseMode.HTML)
        
        try:
            await bot.send_message(
                chat_id=uid,
                text="ТЫ ПРИНЯТ!\n\nВступай в закрытый чат — там весь профит",
                reply_markup=join_kb(),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление пользователю {uid}: {e}")
        
        pending_applications.pop(uid, None)
    else:
        # Сохраняем отклонение в БД
        db.reject_user(uid, callback.from_user.id)
        
        await callback.message.edit_text("❌ Напиши причину отклонения:", parse_mode=ParseMode.HTML)
        await state.set_state(Admin.rejection_reason)
        await state.update_data(target=uid)

@router.callback_query(F.data == "check_sub")
async def check_sub(callback: types.CallbackQuery, bot: Bot):
    if await is_subscribed(bot, callback.from_user.id):
        await eternal_photo(callback, bot, "ПРОВЕРКА ПРОЙДЕНА!\n\nТы в закрытом чате\nТеперь ты один из нас")
    else:
        await callback.answer("Ты ещё не в группе!", show_alert=True)

@router.message(Admin.rejection_reason)
async def rejection_reason(message: types.Message, state: FSMContext, bot: Bot):
    await delete_user_messages(message, bot)
    data = await state.get_data()
    uid = data["target"]
    reason = message.text

    try:
        await bot.send_message(
            chat_id=uid,
            text=f"ЗАЯВКА ОТКЛОНЕНА\n\nПричина:\n{reason}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить причину отклонения пользователю {uid}: {e}")
    
    await bot.edit_message_text(
        f"ОТКЛОНЕНО\n\nПричина:\n{reason}",
        ADMIN_ID,
        pending_applications[uid]["admin_msg_id"],
        parse_mode=ParseMode.HTML
    )
    pending_applications.pop(uid, None)
    await state.clear()

# ====================== ЛОВИМ ВСЁ ======================
@router.message()
async def catch_all(message: types.Message, bot: Bot):
    # Логируем chat_id для групп
    if message.chat.type in ["group", "supergroup"]:
        print(f"💡 ID ГРУППЫ: {message.chat.id}")
        print(f"   Название: {message.chat.title}")
        return
    
    if message.from_user.id in ACCEPTED_USERS:
        return
    await delete_user_messages(message, bot)