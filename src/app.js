const cors = require('cors');
const express = require('express');
const routes = require('./routes');

const app = express();

app.use(cors());
app.use(express.json());
app.get('/health', (_req, res) => res.status(200).json({ status: 'ok' }));
app.use(routes);

module.exports = app;
