const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const port = 8080;

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });


app.use(express.static('public'));

wss.on('connection', (ws) => {
    console.log('New client connected');

    ws.send(JSON.stringify({ message: 'Connected to server' }));

    ws.on('message', (msg) => {
        value = msg.toString();
        console.log('Received:', msg);
        wss.clients.forEach((client) => {
            // just send messages between pepper and the webapp
            if (client.readyState === WebSocket.OPEN && client !== ws) {
                client.send(JSON.stringify({ type: 'command', value }));
            }
        });

    });

    ws.on('close', () => console.log('Client disconnected'));
});

server.listen(port, () => {
    console.log(`Server listening at http://localhost:${port}`);
}); 