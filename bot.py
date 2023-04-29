import datetime
from dotenv import load_dotenv
import sqlite3
import asyncio
import re
import os
from aiohttp import ClientSession
from aiohttp import TCPConnector
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from telebot import asyncio_helper
#asyncio_helper.proxy = 'http://proxy.server:3128'

load_dotenv()

pathToBot = os.getcwd()
bot = AsyncTeleBot(str(os.environ.get('TELEBOT_TOKEN')), parse_mode=None)
vk_token = str(os.environ.get('VK_TOKEN'))
dbFileName = os.path.join(pathToBot, str(os.environ.get('DbFileName')))
userReceivingANotif = list(map(int, str(os.environ.get('UserReceivingANotif')).split('.')))
admins = list(map(int, os.environ.get('Admins').split('.')))
public_id = "192575417"

sendingEveryTime = True

@bot.message_handler(commands=['start'])
async def start_message(message):
    us_id = message.from_user.id
    us_name = message.from_user.first_name
    if message.from_user.last_name:
        us_sname = message.from_user.last_name
    else:
        us_sname = ""
    if message.from_user.username:
        username = message.from_user.username
    else:
        username = ""
    priority = 0

    if await executeQuery("INSERT INTO users (user_id, user_name, user_surname, username, priority) VALUES ('" + str(us_id) + "', '" + us_name + "', '" + us_sname + "', '" + username + "', '" + str(priority) + "');"):
        await bot.send_message(message.chat.id, 'Добро пожаловать! Ваша заявка была отослана администраторам на усмотрение.')
        msgToAdmins = us_name + " " + us_sname + " подал заявку на подписку."
        await messToGroup(admins, msgToAdmins, ["Добавить пользователя", "add_user-"+str(us_id)])
    else:
        await bot.send_message(message.chat.id, 'Ошибка.\n(возможно, ты уже подписался и эта функция бесполезна для тебя,\nесли нет, то напиши тому дебилу, который этого бота сделал)')

@bot.message_handler(commands=['start_bot'])
async def start_bot_message(message):
    global sendingEveryTime
    if await checkPriority(message.chat.id, admins):
        await bot.send_message(message.chat.id, 'Запускаю торпеду обратно......')
        await executeQuery('UPDATE bot_settings SET value = 1 WHERE name = "sendingEveryTime";')
        sendingEveryTime = True
        asyncio.create_task(checkStatement())

@bot.message_handler(commands=['stop_bot'])
async def stop_bot_message(message):
    global sendingEveryTime
    if await checkPriority(message.chat.id, admins):
        await bot.send_message(message.chat.id, 'Cворачиваем тут все, понятно?!')
        await executeQuery('UPDATE bot_settings SET value = 0 WHERE name = "sendingEveryTime";')
        sendingEveryTime = False

@bot.message_handler(commands=['check_vk'])
async def check_vk_message(message):
    try:
        async with ClientSession(connector=TCPConnector(ssl=False), trust_env=True) as session:
            url = "https://api.vk.com/method/wall.get?access_token=" + vk_token + "&owner_id=-" + public_id + "&count=1&filter=owner&v=5.131"
            async with session.get(url=url, ssl=False) as response:
                jsonRes = await response.json()
                await bot.send_message(message.from_user.id, jsonRes['response']['items'][0]['text'])
        return
    except Exception as err:
        print('Error: ', str(err))
        return

@bot.message_handler(commands=['help', '?'])
async def check_vk_message(message):
    await send_help_message(message)

async def send_help_message(message):
    text = ("Функции:\n"
            "    1. /start\n"
            "    2. /help и /? и памаги\n"
            "    3. привет\n"
            "    4. расскажи о сане\n"
            "    5. /check_vk\n")
    await bot.send_message(message.from_user.id, text)


@bot.message_handler(content_types=['text'])
async def get_text_messages(message):
    if message.text.lower() == 'привет':
        await bot.send_message(message.from_user.id, 'Привет!')
    elif message.text.lower() == 'расскажи о сане':
        await bot.send_message(message.from_user.id, articleAboutSanya())
    elif message.text.lower() == 'памаги':
        await send_help_message(message)

def articleAboutSanya() -> str:
    text =  ("  Саня - древнемифологическое существо, которое имеет свое происхождение в русской народной культуре. Оно является частью богатого склада народной мифологии. В этой статье мы рассмотрим некоторые факты о Сане.\n"
"    1. Саня является существом русской мифологии, которое имеет в своем составе черты разных животных - голову коровы, тело кабана, ягненок и коза. Кроме того, Саня часто искусно обладал человеческими способностями.\n"
"    2. Саня часто описывается как лесной человек с удивительной силой и гибкостью. Его кожа была наделена особыми свойствами, что давало ему возможность обходиться без одежды даже в холодном климате.\n"
"    3. Легенды о Сане существовали в разных регионах России, включая Урал, Сибирь и Дальний Восток. Существуют также места, связанные с Саней, которые можно посетить, например, гора Сань добав на Урале.\n"
"    4. Саня часто ассоциируется с лесом и природой, а в его традиционных изображениях можно увидеть различных животных и птиц, например, орлов или тетеревов.\n"
"    5. Эксперты утверждают, что Саня мог возникнуть на основе старых религиозных верований. В свою очередь, некоторые ученые считают, что в основе легенд о Сане лежат реальные случаи встречи с дикими людьми, которые в старинное время могли жить в лесу.\n"
"   В заключении, Саня - это потрясающее древнемифологическое существо, которое настоящее чудо в народной мифологии. Разные версии легенд и рассказов об этом персонаже позволяют нам глубже понять представления и верования наших далеких предков.")
    return text



async def add_button(btnText, callbackData):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btnText, callback_data=callbackData))
    return markup

async def add_buttons(vendors, rowWidth):
    btns = []
    for x in range(0,len(vendors),rowWidth):
        temp_list = []
        for y in range(rowWidth):
            if x+y<len(vendors):
                temp_list.append(InlineKeyboardButton(vendors[x+y]['vendor'], callback_data=vendors[x+y]['callbackData']))
        btns.append(temp_list)
    return InlineKeyboardMarkup(btns)



@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    callData = re.split('-', call.data, 1)
    if callData[0] == "add_user":
        await executeQuery("UPDATE users SET priority = 1 WHERE user_id = '" + str(callData[1]) + "';")
        user = await executeQuery('SELECT * FROM users WHERE user_id = ' + str(callData[1]), True)
        await messToGroup(admins, "Заявка от '" + user[0][2] + " " + user[0][3] + "' была одобрена.")
        await bot.send_message(callData[1], "Ваша заявка была одобрена!", parse_mode="HTML")
        await bot.edit_message_text(text=call.message.text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup='')

async def checkPriority(id, group):
    userPriority = (await executeQuery('SELECT * FROM users WHERE user_id = ' + str(id), True))
    if len(userPriority) == 0:
        return False
    elif userPriority[0][5] not in group:
        return False
    else:
        return True

async def executeQuery(query, fetchall = False):
    successQuery = True
    rows = []
    try:
        conn = sqlite3.connect(dbFileName)
        cursor = conn.cursor()
        cursor.execute(query)
        if fetchall:
            rows = cursor.fetchall()
        conn.commit()
    except Exception as err:
        print('Query Failed. \nError: ', str(err))
        successQuery = False
    finally:
        conn.close()
        if fetchall:
            return rows
        else:
            return successQuery


async def messToGroup(groupList, message, reply_markup=None):
    for user in await executeQuery('SELECT * FROM users', True):
        if user[5] in groupList:
            if reply_markup:
                await bot.send_message(user[1], message, parse_mode = 'HTML', reply_markup=await add_button(reply_markup[0], reply_markup[1]))
            else:
                await bot.send_message(user[1], message, parse_mode = 'HTML')

async def requestToVkGroup():
    try:
        async with ClientSession(connector=TCPConnector(ssl=False), trust_env=True) as session:
            url = "https://api.vk.com/method/wall.get?access_token=" + vk_token + "&owner_id=-" + public_id + "&count=1&filter=owner&v=5.131"
            async with session.get(url=url, ssl=False) as response:
                jsonRes = await response.json()
                await messToGroup(userReceivingANotif, jsonRes['response']['items'][0]['text'])
                await asyncio.sleep(3600)
        return
    except Exception as err:
        print('Error: ', str(err))
        return



async def checkStatement():
    global sendingEveryTime
    try:
        while True:
            load_dotenv()
            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
            weekno = datetime.datetime.today().weekday()

            if sendingEveryTime and weekno<5:
                if now.hour == int(os.environ.get('HOUR_TO_SENDING')):
                    await asyncio.create_task(requestToVkGroup())
                else:
                    await asyncio.sleep(3600)
            else:
                break
    except Exception as err:
        print('Error: ', str(err))


async def main():
    asyncio.create_task(checkStatement())
    await bot.polling(non_stop=True, request_timeout=40)

if __name__ == '__main__':
	asyncio.get_event_loop().run_until_complete(main())