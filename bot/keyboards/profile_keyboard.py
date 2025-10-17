from gc import callbacks

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.locale.get_lang import get_localized_text


def get_profile_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_localized_text(lang, "profile_buttons.edit"), callback_data="edit_profile"),
            InlineKeyboardButton(text=get_localized_text(lang, "profile_buttons.lang"), callback_data="change_lang")],
            [InlineKeyboardButton(text=get_localized_text(lang, "profile_buttons.back"), callback_data="back_profile")],
        ]
    )

def get_profile_edit_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_localized_text(lang, "profile_edit.name"), callback_data="edit_name"),
                InlineKeyboardButton(text=get_localized_text(lang, "profile_edit.phone"), callback_data="edit_phone")
            ],
            [
                InlineKeyboardButton(text=get_localized_text(lang, "profile_edit.email"), callback_data="edit_email"),
            ],
            [
                InlineKeyboardButton(text="↩️ " + get_localized_text(lang, "profile_edit.back"), callback_data="back_profile_show")
            ]
        ]
    )
    return kb