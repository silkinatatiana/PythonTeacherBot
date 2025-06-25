from config import Config
from db import DataBase

import asyncio
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from io import BytesIO
from time import sleep
import requests
import random


class PythonLessons:
    def __init__(self):
        self.headers = {"User-Agent":
                            "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5 (.NET CLR 3.5.30729)"}
        self.main_link = 'https://proproprogs.ru/'
        self.sections_dict = self.get_sections()

    def get_sections(self):
        """Получаем ссылки на названия разделов и ссылки на них"""
        sections_dict = {}
        response = requests.get(self.main_link + 'python_base/', self.headers)
        soup = BeautifulSoup(response.text, 'lxml')
        content = soup.find('div', class_='content-text')
        topic_blocks = content.find_all('div', class_='list-topic')

        for block in topic_blocks:
            section_name = block.find('p').text.strip()
            subsections_dict = {}

            links = block.find_all('a', href=True)
            for link in links:
                subsection_name = link.text.strip()
                subsection_url = self.main_link + link['href']
                subsections_dict[subsection_name] = subsection_url
            sections_dict[section_name] = subsections_dict
        return sections_dict

    def get_content(self, section, subsection):
        """Получаем информацию по выбранной теме"""
        if section not in self.sections_dict or subsection not in self.sections_dict[section]:
            print('На эту тему пока нет учебного материала')
            return

        url = self.sections_dict[section][subsection]
        response = requests.get(url, headers=self.headers)
        sleep(1)
        soup = BeautifulSoup(response.text, 'lxml')

        div = soup.find('div', class_='content-text')
        title = div.find('h1').text.strip()
        rutube_link = div.find('div', class_='title').find_all('a', href=True)[1]['href']
        content = [p.get_text(strip=True).replace('\r\n', ' ') for p in div.find_all('p')[1:] if
                   not p.has_attr('style') and '#' not in p.text]

        text = f"{title}\n\n{' '.join(content)}"
        video = f"\n\nСсылка на видеоурок: {rutube_link}"
        return text, video


class BotTG:
    def __init__(self):
        self.bot = Bot(Config.TOKEN)
        self.dp = Dispatcher()
        self.lessons = None
        self.register_handlers()
        self.user_states = {}
        self.db_instance = DataBase()

    def register_handlers(self):
        self.lessons = PythonLessons()
        self.dp.message(CommandStart())(self.process_start_command)
        self.dp.message(Command('sections'))(self.get_sections_list)
        self.dp.message.register(
            self.choose_section, F.text.in_(self.lessons.get_sections().keys()))
        self.dp.message.register(self.choose_subsection, F.text)

    async def process_start_command(self, message: Message):
        await message.answer('Привет! Я бот, который помогает учить Python.\n'
                             'Чтобы начать учиться - отправь команду /sections')

    async def get_sections_list(self, message: Message):
        sections = self.lessons.get_sections()
        response = "Доступные разделы:\n\n" + '\n'.join(sections.keys())
        await message.answer(response)

    async def choose_section(self, message: Message):
        self.user_states[message.from_user.id] = message.text

        if message.text not in self.lessons.get_sections():
            await message.answer('На эту тему пока нет учебного материала.\nВыбери что-то из /sections')
        else:
            subsections = self.lessons.get_sections()[message.text]
            response = [
                f"{i}) {name}"
                for i, name in enumerate(subsections.keys(), 1)
            ]
            await message.answer(f"Доступные подразделы по теме '{message.text}':\n\n" + "\n".join(response))

    async def choose_subsection(self, message: Message):
        user_id = message.from_user.id
        if user_id not in self.user_states:
            await message.answer("Сначала выберите раздел через /sections")
            return

        section = self.user_states[user_id]
        subsection = message.text
        all_subsections = self.lessons.get_sections()[section]

        if subsection not in all_subsections:
            await message.answer('На эту тему пока нет учебного материала')
        else:
            content, video_url = self.lessons.get_content(section, subsection)
            file_data = BytesIO(content.encode('utf-8'))
            file_data.name = f"{subsection}.txt"

            input_file = BufferedInputFile(file=file_data.getvalue(), filename=f"{subsection}.txt")
            await message.answer_document(input_file)
            if video_url:
                await message.answer(video_url)
            await asyncio.sleep(3)
            
            tasks = await asyncio.to_thread(
                self.db_instance.show_table,
                section=section,
                subsection=subsection
            )
            if tasks:
                random_task = random.choice(tasks)
                button_yes = InlineKeyboardButton(text='Да',
                                                callback_data=f"task_{random_task[0]}")
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[button_yes]])
                await message.answer(
                    text='Хочешь решить задачи на пройденную тему?',
                    reply_markup=keyboard)

    async def run(self):
        try:
            print("Бот успешно запущен!")
            await self.dp.start_polling(self.bot)
        except asyncio.CancelledError:
            pass
        finally:
            await self.bot.session.close()


async def main():
    bot = BotTG()
    await bot.run()


if __name__ == '__main__':
    asyncio.run(main())
