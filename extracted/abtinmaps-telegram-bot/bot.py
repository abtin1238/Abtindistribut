import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from releases import Release, get_release

FEATURES = (
    "<b>امکانات آبتین مپس</b>\n\n"
    "• مسیریابی هوشمند و نمایش مسیر روی نقشه\n"
    "• نقشه‌های آفلاین استانی برای استفاده بدون اینترنت\n"
    "• جست‌وجوی مکان، آدرس و نقاط موردنظر\n"
    "• راهنمای صوتی مسیر و بسته‌های صوتی قابل دانلود\n"
    "• نمای سه‌بعدی نقشه و مدل خودرو\n"
    "• HUD برای نمایش اطلاعات مسیر\n"
    "• ذخیره مکان‌های موردعلاقه و نقاط شخصی\n"
    "• تنظیمات کامل مسیر، نقشه و ظاهر برنامه\n"
    "• پشتیبانی از زبان و بسته‌های زبانی\n"
    "• دریافت به‌روزرسانی‌های نسخه‌های جدید"
)

HELP = (
    "<b>راهنمای نصب</b>\n\n"
    "۱. روی دکمه دانلود اندروید بزنید.\n"
    "۲. فایل APK را دریافت و نصب کنید.\n"
    "۳. دسترسی مکان‌یابی را فعال کنید.\n"
    "۴. نقشه منطقه موردنظر را از بخش نقشه‌های آفلاین دانلود کنید.\n\n"
    "برای نصب نسخه جدید، نسخه قبلی را حذف نکنید تا اطلاعات برنامه حفظ شود."
)


def welcome() -> str:
    return (
        "<b>آبتین مپس</b>\n"
        "مسیریاب هوشمند آفلاین و سه‌بعدی\n\n"
        "با آبتین مپس مسیرت را هوشمندتر، سریع‌تر و بدون وابستگی دائمی به اینترنت پیدا کن.\n\n"
        "از منوی زیر امکانات برنامه را ببین و نسخه اندروید را دانلود کن."
    )


def about(rel: Release) -> str:
    version = f"نسخه فعلی: <b>{rel.version}</b>\n" if rel.version else ""
    return (
        "<b>درباره آبتین مپس</b>\n\n"
        "آبتین مپس یک مسیریاب ایرانی با تمرکز بر نقشه‌های آفلاین، تجربه سه‌بعدی و راهنمایی هوشمند مسیر است.\n\n"
        f"{version}"
        "مناسب برای سفر، استفاده روزمره و مناطقی با اینترنت ضعیف."
    )


def menu(rel: Release) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("معرفی آبتین مپس", callback_data="about"),
         InlineKeyboardButton("امکانات برنامه", callback_data="features")],
        [InlineKeyboardButton("دانلود نسخه اندروید", url=rel.apk_url)],
        [InlineKeyboardButton("راهنمای نصب", callback_data="help"),
         InlineKeyboardButton("آخرین نسخه", url=rel.page_url)],
        [InlineKeyboardButton("اشتراک‌گذاری با دوستان",
                              switch_inline_query="آبتین مپس؛ مسیریاب هوشمند آفلاین و سه‌بعدی")],
    ])


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="home")]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rel = await get_release()
    await update.message.reply_text(welcome(), parse_mode=ParseMode.HTML, reply_markup=menu(rel))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rel = await get_release()
    await update.message.reply_text(HELP, parse_mode=ParseMode.HTML, reply_markup=menu(rel))


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rel = await get_release()
    if query.data == "home":
        await query.edit_message_text(welcome(), parse_mode=ParseMode.HTML, reply_markup=menu(rel))
    elif query.data == "about":
        await query.edit_message_text(about(rel), parse_mode=ParseMode.HTML, reply_markup=back_menu())
    elif query.data == "features":
        await query.edit_message_text(FEATURES, parse_mode=ParseMode.HTML, reply_markup=back_menu())
    elif query.data == "help":
        await query.edit_message_text(HELP, parse_mode=ParseMode.HTML, reply_markup=back_menu())


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Telegram update error: {context.error}", flush=True)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_error_handler(error_handler)
    print("Abtin Maps Telegram bot is running", flush=True)
    # drop_pending_updates: after a Railway restart/redeploy don't replay old taps.
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
