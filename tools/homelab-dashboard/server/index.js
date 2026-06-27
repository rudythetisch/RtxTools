const express = require('express');
const cors = require('cors');
const path = require('path');

const inventoryRoutes = require('./routes/inventory');
const statusRoutes = require('./routes/status');
const actionsRoutes = require('./routes/actions');
const npmRoutes = require('./routes/npm');

const app = express();
const PORT = process.env.PORT || 8160;
const isProd = process.env.NODE_ENV === 'production';

app.use(cors());
app.use(express.json());

app.use('/api/inventory', inventoryRoutes);
app.use('/api/status', statusRoutes);
app.use('/api/actions', actionsRoutes);
app.use('/api/npm', npmRoutes);

if (isProd) {
  app.use(express.static(path.join(__dirname, '../client/dist')));
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../client/dist/index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`Homelab Dashboard running on http://localhost:${PORT}`);
});
