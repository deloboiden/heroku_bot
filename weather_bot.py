import telepot
import time, datetime
import schedule
import sqlite3
import sys
import json
import requests as req
from requests.exceptions import HTTPError
import matplotlib.pyplot as plt
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telepot.loop import MessageLoop
from telepot.delegate import per_chat_id, create_open, pave_event_space

TOKEN = '698304710:AAGxfMDUIB-wBXnoNGGtFlE9r1UHAkMvj2g' # Telegrams bot token
admin = 268115509  # admin's id in Telegram
yandexWeatherKey = "0757853c-3e4d-4c29-b4a1-bd0402abd9db" # yandex

class YandexWeatherGetter():
    def __init__(self, key, latetude, longetude):
        self.key = key
        self.latetude = latetude
        self.longetude = longetude
                   
    def GetWeather(self):
        response = req.get("https://api.weather.yandex.ru/v2/forecast?lat={}&lon={}&lang=ru_RU&limit=1".format(
            self.latetude, self.longetude), headers={'X-Yandex-API-Key':self.key})
        response.raise_for_status()
        if response.status_code == 200:
            data = json.loads(response.text)
            return data
        else:
            raise Exception("error, response code = %d" % esponse.status_code)
            

class Weather_bot(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.markup = ""
        self.ttime = 0
        self.timeDict = {'day': 86400, '3 days': 259200, 'week': 604800, 'mounth': 2592000}

    def weather_predict(self, pressureArray):
        sumX, sumY, sumX2, sumXY = 0, 0, 0, 0
        for i in range(0, len(pressureArray)):
            sumX += i
            sumX2 += i * i
            sumY += pressureArray[i]
            sumXY += pressureArray[i] * i
        delta = len(pressureArray) * sumXY - sumX * sumY
        delta /= (len(pressureArray) * sumX2 - sumX * sumX)
        delta *= len(pressureArray)
        if delta < -150:
            return "the weather will get worse very quickly"
        if -150 <= delta <= -50:
            return "the weather will get worse"
        if -50 <= delta <= 50:
            return "most likely the weather will not change"
        if 50 <= delta <= 150:
            return "the weather will get better"
        if delta > 150:
            return "the weather will get better very quickly"
        return "odd testimony some wild"

    def open(self, initial_msg, seed):
        self.markup = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text='weather now')],
            [KeyboardButton(text='weather predict')],
            [KeyboardButton(text='statistic')],
        ])
        hour = datetime.datetime.now().hour
        if 6 <= hour < 12:
            self.sender.sendMessage("Good morning", reply_markup=self.markup)
        elif 12 <= hour < 17:
            self.sender.sendMessage("Good day", reply_markup=self.markup)
        elif 17 <= hour < 23:
            self.sender.sendMessage("Good evening", reply_markup=self.markup)
        elif 23 <= hour or hour < 6:
            self.sender.sendMessage("Good night", reply_markup=self.markup)
        return True

    def SaveGraphic(self, x, y):
        plt.plot(x, y, color='r')
        plt.tight_layout()
        plt.savefig('graphic.png', type='png')
        plt.close()
        return 'graphic.png'

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        command = msg['text']
        conn = sqlite3.connect("weather_data.db")
        cursor = conn.cursor()

        if command == 'weather now':
            try:
                cursor.execute("select temperature, pressure, humidity, wind_speed," \
                "wind_dir, condition from data order by id desc LIMIT 1")
            except sqlite3.DatabaseError as err:
                self.bot.sendMessage(admin, "error with database" + str(err))
            else:
                temp, pres, humi, win_sp, win_dir, cond, = cursor.fetchone()
                self.sender.sendMessage("temperature: {} C \npressure: {} mm Hg \n" \
                    "humidity: {} % \nwind: {} m/s direction: {} \ncondition: {}".format(
                    round(temp, 2), round(pres, 2), round(humi, 2), win_sp, win_dir, cond))
        elif command == 'weather predict':
            pressureArray = list()
            timestamp = datetime.datetime.now().timestamp()
            sql = "select pressure from data where timestamp between {} and {}".format(
                timestamp - 36000, timestamp)
            try:
                for row in cursor.execute(sql):
                    pressureArray.append(row[0])
            except sqlite3.DatabaseError as err:
                self.bot.sendMessage(admin, "error with database" + str(err))
            else:
                if len(pressureArray) < 7:
                    self.sender.sendMessage("Sorry, we don't have actual data right now")
                    self.bot.sendMessage(admin, "no data for week")
                else:
                    self.sender.sendMessage("here weather predict for now:")
                    self.sender.sendMessage(self.weather_predict(pressureArray))
        elif command == 'statistic':
            self.markup = ReplyKeyboardMarkup(keyboard=[
                [dict(text='day')],
                [dict(text='3 days')],
                [dict(text='week')],
                [dict(text='mounth')],
                [dict(text='back to main')],
            ])
            self.sender.sendMessage(command, reply_markup=self.markup)
        elif command in ['day', '3 days', 'week', 'mounth']:
            self.markup = ReplyKeyboardMarkup(keyboard=[
                [dict(text='temperature')],
                [dict(text='pressure')],
                [dict(text='humidity')],
                [dict(text='wind_speed')],
                [dict(text='back to main')],
            ])
            self.sender.sendMessage(command, reply_markup=self.markup)
            self.ttime = self.timeDict[command]
        elif command == 'back to main':
            self.markup = ReplyKeyboardMarkup(keyboard=[
                [dict(text='weather now')],
                [dict(text='weather predict')],
                [dict(text='statistic')],
            ])
            self.sender.sendMessage(command, reply_markup=self.markup)
        elif command in ['temperature', 'pressure', 'humidity', 'wind_speed']:
            x, y = [], []
            timestamp = datetime.datetime.now().timestamp()
            sql = "select timestamp, {} from data where timestamp between {} and {}".format(
                command, timestamp - self.ttime, timestamp)
            try:
                for row in cursor.execute(sql):
                    x.append(datetime.datetime.fromtimestamp(row[0]))
                    y.append(row[1])
            except sqlite3.DatabaseError as err:
                self.bot.sendMessage(admin, "error with database" + str(err))
            else:
                path = self.SaveGraphic(x, y)
                self.sender.sendPhoto(open(path, 'rb'))
        cursor.close()
        conn.close()

    def on__idle(self, event):
        #self.markup = ReplyKeyboardRemove()
        self.sender.sendMessage("Good bye", reply_markup=self.markup)


if __name__ == "__main__":
    #инициализируем загрузчик погоды
    weatherGetter = YandexWeatherGetter(yandexWeatherKey, 60.006890, 30.372777)
    #запускаем бота
    bot = telepot.DelegatorBot(TOKEN, [
        pave_event_space()(
            per_chat_id(), create_open, Weather_bot, timeout=300),
    ])
    MessageLoop(bot).run_as_thread()
    print('Listening ...')
    #функция загрузки погоды в базу данных, ошибки отправляются админу
    def InsetrWeather():
        try:
            data = weatherGetter.GetWeather()
            conn = sqlite3.connect("weather_data.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO data (timestamp, temperature, pressure, humidity, wind_speed," \
                "wind_dir, condition) VALUES ({}, {}, {}, {}, {}, '{}', '{}')".format(data['now'],
                                                                                     data['fact']['temp'],
                                                                                     data['fact']['pressure_mm'],
                                                                                     data['fact']['humidity'],
                                                                                     data['fact']['wind_speed'],
                                                                                     data['fact']['wind_dir'],
                                                                                     data['fact']['condition']))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            bot.sendMessage(admin, "error: {}".format(e))
    # запускаем таймер
    schedule.every(1).minutes.do(InsetrWeather)
    while 1:
        schedule.run_pending()
        time.sleep(10)

