const http = require ('http');
const express = require ('express');
const app = express ();
const PORT = 3000;

app.use (express.json ());

app.post ('/ask', async (req, res) => {
  try {
    const {chatId, question} = req.body;
    if (!question) {
      return res.status (400).json ({error: 'Введите сообщение!'});
    }
    console.log (question);
    res.json ({
      answer: 'Спасибо за вопрос!',
    });
  } catch (error) {
    console.error ('Error:', error);
  }
});

app.listen (PORT, '127.0.0.1', () => {
  console.log (`Server running at http://127.0.0.1:${PORT}/`);
});
