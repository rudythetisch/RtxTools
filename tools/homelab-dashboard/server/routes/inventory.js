const express = require('express');
const fs = require('fs');
const path = require('path');

const router = express.Router();
const DATA_FILE = path.join(__dirname, '../data/inventory.json');

function load() {
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function save(data) {
  fs.writeFileSync(DATA_FILE + '.tmp', JSON.stringify(data, null, 2));
  fs.renameSync(DATA_FILE + '.tmp', DATA_FILE);
}

router.get('/', (req, res) => {
  res.json(load());
});

router.get('/devices', (req, res) => {
  res.json(load().devices);
});

router.post('/devices', (req, res) => {
  const data = load();
  const device = { ...req.body, id: req.body.id || Date.now().toString() };
  data.devices.push(device);
  save(data);
  res.status(201).json(device);
});

router.put('/devices/:id', (req, res) => {
  const data = load();
  const idx = data.devices.findIndex(d => d.id === req.params.id);
  if (idx === -1) return res.status(404).json({ error: 'Not found' });
  data.devices[idx] = { ...data.devices[idx], ...req.body };
  save(data);
  res.json(data.devices[idx]);
});

router.delete('/devices/:id', (req, res) => {
  const data = load();
  data.devices = data.devices.filter(d => d.id !== req.params.id);
  save(data);
  res.json({ ok: true });
});

router.get('/services', (req, res) => {
  res.json(load().services);
});

router.post('/services', (req, res) => {
  const data = load();
  const service = { ...req.body, id: req.body.id || Date.now().toString() };
  data.services.push(service);
  save(data);
  res.status(201).json(service);
});

router.put('/services/:id', (req, res) => {
  const data = load();
  const idx = data.services.findIndex(s => s.id === req.params.id);
  if (idx === -1) return res.status(404).json({ error: 'Not found' });
  data.services[idx] = { ...data.services[idx], ...req.body };
  save(data);
  res.json(data.services[idx]);
});

router.delete('/services/:id', (req, res) => {
  const data = load();
  data.services = data.services.filter(s => s.id !== req.params.id);
  save(data);
  res.json({ ok: true });
});

module.exports = router;
