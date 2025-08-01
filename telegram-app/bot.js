require ('dotenv').config ({path: '../.env'});
const axios = require ('axios');
const TelegramBot = require ('node-telegram-bot-api');
const token = process.env.TELEGRAM_BOT_TOKEN;
const bot = new TelegramBot (token, {polling: true});

const SERVERURL = 'http://127.0.0.1:3000/ask';

if (!token) {
  console.error ('Токен не найден!');
  process.exit (1);
}

bot.on ('message', async msg => {
  const chatId = msg.chat.id;
  const message = msg.text;
  const user = msg.from;

  if (message === '/start') {
    await bot.sendMessage (
      chatId,
      `Добро пожаловать, ${user.first_name} ${user.last_name}!`
    );
  } else if (message) {
    try {
      const waitText = await bot.sendMessage (chatId, 'Запрос отправлен');
      const response = await axios.post (SERVERURL, {
        chatId: chatId,
        question: message,
      });
      let answer = response.data.answer;
      await bot.editMessageText (answer, {
        chat_id: waitText.chat.id,
        message_id: waitText.message_id,
      });
      console.log (response.data.answer);
    } catch (error) {
      console.log (error);
      await bot.sendMessage (
        chatId,
        'Произошла ошибка при обработке сообщения!'
      );
    }
  }
});
const commands = [
  {
    command: 'start',
    description: 'Запуск бота',
  },
  {
    command: 'help',
    description: 'Раздел помощи',
  },
];

bot.setMyCommands (commands);
