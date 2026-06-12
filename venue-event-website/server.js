const express = require('express');
const path = require('path');
const https = require('https');
const http = require('http');
const forge = require('node-forge');

const app = express();

// Serve static files from public directory
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// ============ API ROUTES (Proxy to Docker Services) ============

app.get('/api/artists', async (req, res) => {
  try {
    const response = await fetch('http://127.0.0.1:8003/lineup/concert-2026-jkt');
    if (!response.ok) throw new Error('Artist service error');
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Error fetching artists:', error.message);
    res.status(502).json({ error: 'Artist service unavailable' });
  }
});

app.get('/api/capacity', async (req, res) => {
  try {
    const response = await fetch('http://127.0.0.1:8002/capacity/concert-2026-jkt');
    if (!response.ok) throw new Error('Venue service error');
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Error fetching capacity:', error.message);
    res.status(502).json({ error: 'Venue service unavailable' });
  }
});

app.get('/api/orders', async (req, res) => {
  try {
    const response = await fetch('http://127.0.0.1:8001/orders');
    if (!response.ok) throw new Error('Ticketing service error');
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Error fetching orders:', error.message);
    res.status(502).json({ error: 'Ticketing service unavailable' });
  }
});

app.post('/api/orders', async (req, res) => {
  try {
    const payload = {
      concert_id: "concert-2026-jkt",
      ...req.body
    };
    const response = await fetch('http://127.0.0.1:8001/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    console.error('Error creating order:', error.message);
    res.status(502).json({ error: 'Ticketing service unavailable' });
  }
});

// Serve frontend SPA
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Generate self-signed SSL certificate using node-forge
console.log('\n⏳ Generating SSL certificate...');

const pki = forge.pki;
const keys = pki.rsa.generateKeyPair(2048);
const cert = pki.createCertificate();

cert.publicKey = keys.publicKey;
cert.serialNumber = '01' + forge.util.bytesToHex(forge.random.getBytesSync(19));
cert.validity.notBefore = new Date();
cert.validity.notAfter = new Date();
cert.validity.notAfter.setFullYear(cert.validity.notBefore.getFullYear() + 1);

const attrs = [
  { name: 'commonName', value: 'localhost' },
  { name: 'organizationName', value: 'Konseran Dev' },
  { name: 'countryName', value: 'ID' }
];

cert.setSubject(attrs);
cert.setIssuer(attrs);

cert.setExtensions([
  { name: 'basicConstraints', cA: true },
  { name: 'keyUsage', keyCertSign: true, digitalSignature: true, nonRepudiation: true, keyEncipherment: true, dataEncipherment: true },
  { name: 'extKeyUsage', serverAuth: true, clientAuth: true },
  { name: 'subjectAltName', altNames: [
    { type: 2, value: 'localhost' },
    { type: 7, ip: '127.0.0.1' }
  ]}
]);

cert.sign(keys.privateKey, forge.md.sha256.create());

const pemKey = pki.privateKeyToPem(keys.privateKey);
const pemCert = pki.certificateToPem(cert);

console.log('✅ SSL certificate generated!');

const sslOptions = {
  key: pemKey,
  cert: pemCert,
  minVersion: 'TLSv1.2'
};

// HTTPS server on port 443 (default HTTPS port = no port in URL)
https.createServer(sslOptions, app).listen(443, () => {
  console.log(`\n✨ ═══════════════════════════════════════════════════ ✨`);
  console.log(`   Konseran - Premium Event Venue Platform`);
  console.log(`   Server running at: https://localhost`);
  console.log(`✨ ═══════════════════════════════════════════════════ ✨\n`);
});

// HTTP redirect to HTTPS (port 80 -> 443)
const redirectApp = express();
redirectApp.all('*', (req, res) => {
  res.redirect(301, `https://localhost${req.url}`);
});

http.createServer(redirectApp).listen(80, () => {
  console.log('   HTTP redirect (port 80) → https://localhost');
}).on('error', () => {
  // Port 80 might be in use, that's okay
  console.log('   ⚠ Port 80 in use, HTTP redirect skipped');
  console.log('   Open https://localhost directly\n');
});
