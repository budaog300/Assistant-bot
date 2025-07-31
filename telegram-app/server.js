const http = require ('http');
const axios = require ('axios');
const express = require ('express');
const {realpathSync} = require ('fs');
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
    const response = await axios.post ('http://127.0.0.1:8000/ask', {
      query: question,
    });
    console.log (response.data);
    res.json ({
      answer: response.data.answer,
    });
    response.data = {};
  } catch (error) {
    console.error ('Error:', error);
    return res.status (500).json (error);
  }
});

app.listen (PORT, '127.0.0.1', () => {
  console.log (`Server running at http://127.0.0.1:${PORT}/`);
});
