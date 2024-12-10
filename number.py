from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import aiohttp
import asyncio

GOOGLE_API_KEY = 'AIzaSyBy9RaAPzm2WOWePwp9JWD1cUF3bCQsCm0'
TELEGRAM_BOT_TOKEN = '7463187052:AAGa9LAD0qv1UDwBtJxCogGHsZfopnIUDmg'

def format_phone_number(phone_number: str, country_code: str) -> str:
    if phone_number.startswith('+'):
        return phone_number  # already in international format
    if phone_number.startswith('0'):
        phone_number = phone_number[1:]  # remove leading zero
    return f"+{country_code}{phone_number}"

async def get_place_details(place_id: str) -> str:
    async with aiohttp.ClientSession() as session:
        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number&key={GOOGLE_API_KEY}"
        async with session.get(url) as response:
            data = await response.json()
            if 'result' in data:
                result = data['result']
                phone_number = result.get('formatted_phone_number', 'N/A')
                if phone_number != 'N/A':
                    phone_number = format_phone_number(phone_number, '44')  # Assuming UK country code
                return phone_number
            return 'N/A'

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Send me the region and sector in the format:\n\n"
        "/search <region> <sector>"
    )

async def search(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /search <region> <sector>")
        return
    
    region = context.args[0]
    sector = context.args[1]
    
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={sector}+in+{region}&key={GOOGLE_API_KEY}"
    all_results = []
    
    async with aiohttp.ClientSession() as session:
        while url:
            async with session.get(url) as response:
                data = await response.json()
                if 'results' in data:
                    businesses = data['results']
                    all_results.extend(businesses)
                    
                    if 'next_page_token' in data:
                        next_page_token = data['next_page_token']
                        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?pagetoken={next_page_token}&key={GOOGLE_API_KEY}"
                        await asyncio.sleep(2)  # Avoid rate limiting
                    else:
                        url = None  # No more pages
                else:
                    await update.message.reply_text("Error fetching data from Google Places API.")
                    return
    
    tasks = [get_place_details(business['place_id']) for business in all_results[:400]]
    phone_numbers = await asyncio.gather(*tasks)
    
    phone_numbers = [number for number in phone_numbers if number != 'N/A']
    
    if phone_numbers:
        message = "\n".join(phone_numbers)
        if not message:
            message = "No phone numbers found."
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("No results found.")

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('search', search))
    
    application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
