const databaseUtils = require('./utils/databaseUtils');
const http = require('http');
const mongoose = require('mongoose');
const app = require('./app');
const server = http.Server(app);
const {setupWebsocket} = require('./websocket');
setupWebsocket(server);
mongoose.connect(databaseUtils.getDatabaseURI(), databaseUtils.getDatabaseOptions());
server.listen(process.env.LISTEN_PORT);
