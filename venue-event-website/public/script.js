/* ===================================================================
   Konseran - Concert Management Platform JavaScript
   =================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // ── Loader ──
  const loader = document.getElementById('page-loader');
  window.addEventListener('load', () => {
    setTimeout(() => loader.classList.add('hidden'), 800);
  });

  // ── Hero Particles ──
  createParticles();

  // ── Navigation ──
  initNavigation();

  // ── Scroll Animations ──
  initScrollAnimations();

  // ── Load Microservices Data ──
  loadArtists();
  loadCapacity();
  loadOrders();

  // ── Booking Form ──
  initBookingForm();

  // ── Back to Top ──
  initBackToTop();
});

// ═══════════════════════════════════════════════════
// UI Global Handlers
// ═══════════════════════════════════════════════════

function calculateTotal() {
  const type = document.getElementById('bookingType').value;
  const qty = parseInt(document.getElementById('bookingQty').value) || 1;
  const price = type === 'VIP' ? 1500000 : 750000;
  const total = price * qty;
  
  const formatted = new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(total);
  document.getElementById('bookingTotalDisplay').textContent = formatted;
}

// ═══════════════════════════════════════════════════
// Artist Service Integration
// ═══════════════════════════════════════════════════

async function loadArtists() {
  try {
    const res = await fetch('/api/artists');
    if (!res.ok) throw new Error('API Error');
    const data = await res.json();
    renderArtists(data.artists || []);
    
    // Update Stats
    document.getElementById('stat-artists').setAttribute('data-count', (data.artists || []).length);
    initCounters();
  } catch (err) {
    console.error('Failed to load artists:', err);
    document.getElementById('artistsGrid').innerHTML = '<p style="color:var(--color-error); padding: 20px;">Gagal memuat lineup artis. Service unavailable.</p>';
  }
}

function renderArtists(artists) {
  const grid = document.getElementById('artistsGrid');
  grid.innerHTML = '';

  artists.forEach((artist, index) => {
    const card = document.createElement('div');
    card.className = `venue-card animate-on-scroll delay-${(index % 3) + 1}`;
    
    card.innerHTML = `
      <div class="venue-card-image" style="height: 150px; display:flex; align-items:center; justify-content:center; font-size:4rem; background:var(--color-gold-glow);">
        🎸
      </div>
      <div class="venue-card-body">
        <h3 class="venue-card-title">${artist.artist_name}</h3>
        <div class="venue-card-location">📍 ${artist.stage_name}</div>
        <div class="venue-card-info" style="margin-top:10px;">
          <div class="venue-card-capacity">Waktu Tampil: <strong>${artist.start_time}</strong></div>
        </div>
      </div>
    `;
    grid.appendChild(card);
    if (scrollObserver) scrollObserver.observe(card);
  });
}

// ═══════════════════════════════════════════════════
// Venue Service Integration (Capacity)
// ═══════════════════════════════════════════════════

async function loadCapacity() {
  try {
    const res = await fetch('/api/capacity');
    if (!res.ok) throw new Error('API Error');
    const data = await res.json();
    renderCapacity(data);
    
    // Update total capacity stat
    let totalCap = 0;
    data.forEach(d => totalCap += d.capacity);
    document.getElementById('stat-capacity').setAttribute('data-count', totalCap);
    initCounters();
  } catch (err) {
    console.error('Failed to load capacity:', err);
    document.getElementById('capacityGrid').innerHTML = '<p style="color:var(--color-error); padding: 20px;">Gagal memuat kapasitas venue. Service unavailable.</p>';
  }
}

function renderCapacity(capacities) {
  const grid = document.getElementById('capacityGrid');
  grid.innerHTML = '';

  capacities.forEach((cap, index) => {
    const available = cap.capacity - cap.reserved;
    const card = document.createElement('div');
    card.className = `service-item animate-on-scroll delay-${index + 1}`;
    
    card.innerHTML = `
      <div class="service-item-icon">${cap.ticket_type === 'VIP' ? '👑' : '🎫'}</div>
      <div style="flex-grow:1;">
        <h3 class="service-item-title">Kategori ${cap.ticket_type}</h3>
        <div style="display:flex; justify-content:space-between; margin-top:10px; color:var(--color-text-secondary);">
          <span>Total Kapasitas: ${cap.capacity}</span>
          <span>Terisi: <strong style="color:var(--color-gold-primary)">${cap.reserved}</strong></span>
        </div>
        <div style="width:100%; height:8px; background:rgba(255,255,255,0.1); border-radius:4px; margin-top:10px; overflow:hidden;">
          <div style="width:${(cap.reserved/cap.capacity)*100}%; height:100%; background:var(--color-gold-primary);"></div>
        </div>
        <div style="margin-top:10px; font-weight:bold; color:${available > 0 ? '#4caf50' : '#f44336'}">
          Tersedia: ${available} Tiket
        </div>
      </div>
    `;
    grid.appendChild(card);
    if (scrollObserver) scrollObserver.observe(card);
  });
}

// ═══════════════════════════════════════════════════
// Ticketing Service Integration (Orders)
// ═══════════════════════════════════════════════════

async function loadOrders() {
  try {
    const res = await fetch('/api/orders');
    if (!res.ok) throw new Error('API Error');
    const data = await res.json();
    renderOrders(data);
  } catch (err) {
    console.error('Failed to load orders:', err);
    document.getElementById('ordersGrid').innerHTML = '<p style="color:var(--color-error); padding: 20px;">Gagal memuat daftar pesanan. Service unavailable.</p>';
  }
}

function renderOrders(orders) {
  const grid = document.getElementById('ordersGrid');
  grid.innerHTML = '';
  
  if (orders.length === 0) {
    grid.innerHTML = '<p style="color:var(--color-text-secondary); text-align:center;">Belum ada pesanan.</p>';
    return;
  }

  // Render top 5 latest orders (reversed)
  const latestOrders = [...orders].reverse().slice(0, 5);

  latestOrders.forEach((order, index) => {
    const card = document.createElement('div');
    card.className = `service-item animate-on-scroll delay-${index + 1}`;
    
    let statusColor = '#ff9800'; // Pending
    if (order.status === 'CONFIRMED') statusColor = '#4caf50';
    if (order.status === 'FAILED') statusColor = '#f44336';

    const formattedAmount = new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(order.amount);

    card.innerHTML = `
      <div style="flex-grow:1; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <h3 class="service-item-title" style="margin-bottom:5px;">${order.participant_name} <span style="font-size:0.8em; color:var(--color-text-muted);">(${order.ticket_type} x${order.quantity})</span></h3>
          <p style="color:var(--color-text-secondary); font-size:0.9rem;">${formattedAmount} via ${order.payment_method}</p>
        </div>
        <div style="text-align:right;">
          <div style="background:rgba(255,255,255,0.05); padding:6px 12px; border-radius:20px; font-size:0.8rem; border:1px solid ${statusColor}; color:${statusColor}; font-weight:bold;">
            ${order.status}
          </div>
          <div style="font-size:0.75rem; color:var(--color-text-muted); margin-top:5px;">Pay: ${order.payment_status}</div>
        </div>
      </div>
    `;
    grid.appendChild(card);
    if (scrollObserver) scrollObserver.observe(card);
  });
}

function initBookingForm() {
  const form = document.getElementById('bookingForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('submitBooking');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Memproses...';

    const type = document.getElementById('bookingType').value;
    const qty = parseInt(document.getElementById('bookingQty').value) || 1;
    const price = type === 'VIP' ? 1500000 : 750000;
    const amount = price * qty;

    const payload = {
      participant_name: document.getElementById('bookingName').value,
      participant_email: document.getElementById('bookingEmail').value,
      ticket_type: type,
      quantity: qty,
      amount: amount,
      currency: "IDR",
      payment_method: document.getElementById('bookingPayment').value
    };

    try {
      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const result = await res.json();

      if (res.ok) {
        showToast('success', 'Pesanan berhasil dibuat! Notifikasi akan dikirim ke email Anda.');
        form.reset();
        calculateTotal();
        
        // Reload data to show new order & capacity changes (simulated delay for worker to process)
        setTimeout(() => {
          loadOrders();
          loadCapacity();
        }, 1500);
      } else {
        showToast('error', result.detail || result.error || 'Terjadi kesalahan saat membuat pesanan.');
      }
    } catch (err) {
      showToast('error', 'Gagal memproses pesanan. Periksa koneksi Anda.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span class="btn-icon">💳</span> Bayar Sekarang';
    }
  });
}

// ═══════════════════════════════════════════════════
// Boilerplate Visuals
// ═══════════════════════════════════════════════════
function createParticles() {
  const container = document.getElementById('heroParticles');
  if (!container) return;
  for (let i = 0; i < 30; i++) {
    const particle = document.createElement('div');
    particle.className = 'particle';
    particle.style.left = Math.random() * 100 + '%';
    particle.style.animationDelay = Math.random() * 8 + 's';
    particle.style.animationDuration = (6 + Math.random() * 6) + 's';
    particle.style.width = (2 + Math.random() * 3) + 'px';
    particle.style.height = particle.style.width;
    particle.style.opacity = 0.2 + Math.random() * 0.4;
    container.appendChild(particle);
  }
}

function initNavigation() {
  const navbar = document.getElementById('navbar');
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');
  const allNavLinks = document.querySelectorAll('[data-nav]');

  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) navbar.classList.add('scrolled');
    else navbar.classList.remove('scrolled');

    const sections = document.querySelectorAll('section[id]');
    let current = '';
    sections.forEach(section => {
      const top = section.offsetTop - 120;
      if (window.scrollY >= top) current = section.getAttribute('id');
    });

    allNavLinks.forEach(link => {
      link.classList.remove('active');
      if (link.getAttribute('href') === '#' + current) link.classList.add('active');
    });
  });

  navToggle.addEventListener('click', () => {
    navToggle.classList.toggle('active');
    navLinks.classList.toggle('active');
  });

  allNavLinks.forEach(link => {
    link.addEventListener('click', () => {
      navToggle.classList.remove('active');
      navLinks.classList.remove('active');
    });
  });
}

let scrollObserver = null;

function initScrollAnimations() {
  scrollObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

  document.querySelectorAll('.animate-on-scroll').forEach(el => scrollObserver.observe(el));
}

function initCounters() {
  const counters = document.querySelectorAll('[data-count]');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  counters.forEach(counter => observer.observe(counter));
}

function animateCounter(element) {
  const target = parseInt(element.getAttribute('data-count'));
  const duration = 2000;
  const start = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.floor(eased * target);

    element.textContent = current.toLocaleString('id-ID') + (target >= 100 ? '+' : '');

    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

function showToast(type, message) {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✅', error: '❌', warning: '⚠️' };
  toast.innerHTML = `<span class="toast-icon">${icons[type] || '💡'}</span><span class="toast-message">${message}</span>`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

function initBackToTop() {
  const btn = document.getElementById('backToTop');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 600) btn.classList.add('visible');
    else btn.classList.remove('visible');
  });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}
