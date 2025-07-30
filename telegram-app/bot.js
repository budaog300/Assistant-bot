require ('dotenv').config ({path: '../.env'});
const TelegramBot = require ('node-telegram-bot-api');
const token = process.env.TELEGRAM_BOT_TOKEN;
const bot = new TelegramBot (token, {polling: true});

if (!token) {
  console.error ('Токен не найден!');
  process.exit (1);
}

bot.on ('message', msg => {
  const chatId = msg.chat.id;
  const messageText = msg.text;
  const user = msg.from;

  if (messageText === '/start') {
    bot.sendMessage (
      chatId,
      `Welcome to the bot, ${user.first_name} ${user.last_name}!`
    );
  } else if (messageText) {
    bot.sendMessage (chatId, messageText);
    console.log (messageText);
  }
});
