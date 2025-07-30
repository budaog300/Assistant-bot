const http = require ('http');
const PORT = 3000;

const server = http.createServer ((req, res) => {
  if (req.url === '/') {
    res.statusCode = 200;
    res.setHeader ('Content-Type', 'text/html');
    res.end ('<h1>Home Page</h1>');
  } 
});

server.listen (PORT, '127.0.0.1', () => {
  console.log (`Server running at http://127.0.0.1:${PORT}/`);
});
