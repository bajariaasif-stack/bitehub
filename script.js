// Client-side state for menu, reservations, and the current order.
let menuItems = [];

let reservationList = [];

const recentOrders = [
  { id: '#1042', total: 68.5, table: 'Table 3', status: 'Preparing' },
  { id: '#1041', total: 42.0, table: 'Table 1', status: 'Served' },
  { id: '#1040', total: 57.25, table: 'Takeaway', status: 'Ready' }
];

const staffMembers = [
  { name: 'Sofia', role: 'Head Chef', score: 96 },
  { name: 'Daniel', role: 'Floor Manager', score: 91 },
  { name: 'Aisha', role: 'Barista', score: 88 }
];

const kitchenStatus = [
  { label: 'On the pass', value: '3 dishes', state: 'ready' },
  { label: 'In prep', value: '6 dishes', state: 'pending' },
  { label: 'Restock alert', value: 'Lemonade', state: 'alert' }
];

let cart = [];
let currentCategory = 'All';

const money = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2
});

// Generate fallback food artwork when an item has no usable image URL.
function dishPalette(name) {
  const palettes = {
    Roti: ['#d97706', '#fff7ed'],
    Chapati: ['#b45309', '#fffbeb'],
    Paratha: ['#f59e0b', '#fef3c7'],
    Dal: ['#16a34a', '#dcfce7'],
    Chawal: ['#14b8a6', '#ccfbf1'],
    'Dal Chawal': ['#0ea5e9', '#e0f2fe'],
    Buttermilk: ['#38bdf8', '#e0f2fe']
  };

  return palettes[name] || ['#ff7b54', '#fff4e8'];
}

function makeDishArtDataUri(name, accent = '#ff7b54', background = '#fff4e8') {
  const safeLabel = String(name || 'Dish')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  const icons = {
    Roti: "<path d='M155 246C186 205 234 179 300 177C366 175 414 205 445 246C482 294 452 338 389 346C342 352 288 348 241 349C178 350 124 319 155 246Z' fill='rgba(255,255,255,0.54)'/>",
    Chapati: "<path d='M150 245C175 204 225 170 301 172C382 174 433 214 448 252C431 313 385 340 301 342C213 344 167 308 150 245Z' fill='rgba(255,255,255,0.50)'/>",
    Paratha: "<path d='M138 240C168 190 229 155 300 156C382 157 440 196 460 247C431 318 382 344 300 346C215 348 168 319 138 240Z' fill='rgba(255,255,255,0.55)'/>",
    Dal: "<path d='M125 248C172 178 237 160 299 160C375 160 442 196 465 245C437 330 370 344 298 349C222 353 162 325 125 248Z' fill='rgba(255,255,255,0.58)'/>",
    Chawal: "<path d='M120 244C170 182 227 158 300 159C371 160 437 187 467 242C435 325 363 346 299 347C227 349 169 321 120 244Z' fill='rgba(255,255,255,0.62)'/>",
    'Dal Chawal': "<path d='M111 241C162 189 213 170 300 170C380 170 436 188 483 241C454 321 382 346 299 349C227 350 167 323 111 241Z' fill='rgba(255,255,255,0.60)'/>",
    Buttermilk: "<path d='M188 150H412C437 150 456 170 456 196V250C456 323 398 366 300 366C201 366 144 323 144 250V196C144 170 163 150 188 150Z' fill='rgba(255,255,255,0.60)'/>"
  };

  const icon = icons[name] || "<circle cx='300' cy='220' r='120' fill='rgba(255,255,255,0.52)'/>";

  const svg = `
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 420'>
      <defs>
        <linearGradient id='g' x1='0' x2='1'>
          <stop offset='0%' stop-color='${background}' />
          <stop offset='100%' stop-color='${accent}' />
        </linearGradient>
      </defs>
      <rect width='600' height='420' rx='32' fill='url(#g)' />
      <circle cx='500' cy='88' r='52' fill='rgba(255,255,255,0.24)' />
      <path d='M88 304C163 246 218 224 302 228C383 232 434 253 513 304' stroke='rgba(255,255,255,0.46)' stroke-width='16' fill='none' stroke-linecap='round' />
      <ellipse cx='300' cy='235' rx='170' ry='110' fill='rgba(255,255,255,0.16)' />
      ${icon}
      <ellipse cx='300' cy='248' rx='150' ry='66' fill='rgba(255,255,255,0.18)' />
      <text x='300' y='220' text-anchor='middle' font-size='52' font-family='Arial, sans-serif' font-weight='700' fill='#1f2937'>${safeLabel}</text>
      <text x='300' y='295' text-anchor='middle' font-size='22' font-family='Arial, sans-serif' fill='#334155'>BiteHub</text>
    </svg>
  `.trim();

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function normaliseImageUrl(item) {
  const name = item?.name || 'Dish';
  const url = (item?.image_url || '').trim();

  if (!url) {
    const [accent, background] = dishPalette(name);
    return makeDishArtDataUri(name, accent, background);
  }

  if (url.startsWith('data:image/') || url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  const [accent, background] = dishPalette(name);
  return makeDishArtDataUri(name, accent, background);
}

function readLocalImageAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    if (!file || !file.type.startsWith('image/')) {
      reject(new Error('Please choose a valid image file.'));
      return;
    }

    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Unable to read the selected image.'));
    reader.readAsDataURL(file);
  });
}

// Cache the page controls used by the renderers and event handlers.
const categoryFilters = document.getElementById('categoryFilters');
const menuList = document.getElementById('menuList');
const menuSearch = document.getElementById('menuSearch');
const menuEditForm = document.getElementById('menuEditForm');
const menuEditSelect = document.getElementById('menuEditSelect');
const menuEditName = document.getElementById('menuEditName');
const menuEditCategory = document.getElementById('menuEditCategory');
const menuEditPrice = document.getElementById('menuEditPrice');
const menuEditStock = document.getElementById('menuEditStock');
const menuEditImageUrl = document.getElementById('menuEditImageUrl');
const menuImageUpload = document.getElementById('menuImageUpload');
const orderItems = document.getElementById('orderItems');
const recentOrdersBox = document.getElementById('recentOrders');
const popularItems = document.getElementById('popularItems');
const reservationListBox = document.getElementById('reservationList');
const staffList = document.getElementById('staffList');
const kitchenStatusBox = document.getElementById('kitchenStatus');
const salesValue = document.getElementById('salesValue');
const orderCount = document.getElementById('orderCount');
const guestCount = document.getElementById('guestCount');
const alertCount = document.getElementById('alertCount');
const subtotalValue = document.getElementById('subtotalValue');
const serviceValue = document.getElementById('serviceValue');
const totalValue = document.getElementById('totalValue');
const tableSelect = document.getElementById('tableSelect');
const tableLabel = document.getElementById('tableLabel');
const customerName = document.getElementById('customerName');
const customerPhone = document.getElementById('customerPhone');
const customerEmail = document.getElementById('customerEmail');
const customerAddress = document.getElementById('customerAddress');
const paymentMethod = document.getElementById('paymentMethod');
const paymentStatus = document.getElementById('paymentStatus');
const placeOrderBtn = document.getElementById('placeOrderBtn');

// Load menu data from the API, with local defaults if the API is unavailable.
async function loadMenu() {
  try {
      const response = await fetch('/api/menu');
    if (!response.ok) throw new Error('Failed to load menu');
    const data = await response.json();
    menuItems = data.map((item) => ({
      ...item,
      image_url: normaliseImageUrl(item)
    }));
  } catch (error) {
    console.warn('Using fallback menu data:', error);
    menuItems = [
      { id: 1, name: 'Burger', category: 'Main Course', price: 199.0, stock: 10, image_url: makeDishArtDataUri('Burger') },
      { id: 2, name: 'Fries', category: 'Sides', price: 99.0, stock: 20, image_url: makeDishArtDataUri('Fries') },
      { id: 3, name: 'Tea', category: 'Beverages', price: 59.0, stock: 15, image_url: makeDishArtDataUri('Tea') },
      { id: 4, name: 'Pasta', category: 'Main Course', price: 249.0, stock: 8, image_url: makeDishArtDataUri('Pasta') },
      { id: 5, name: 'Salad', category: 'Appetizer', price: 149.0, stock: 14, image_url: makeDishArtDataUri('Salad') },
      { id: 6, name: 'Cake', category: 'Dessert', price: 129.0, stock: 9, image_url: makeDishArtDataUri('Cake') },
      { id: 8, name: 'Chapati', category: 'Main Course', price: 65.0, stock: 24, image_url: makeDishArtDataUri('Chapati') },
      { id: 9, name: 'Paratha', category: 'Main Course', price: 79.0, stock: 22, image_url: makeDishArtDataUri('Paratha') },
      { id: 10, name: 'Dal', category: 'Main Course', price: 129.0, stock: 18, image_url: makeDishArtDataUri('Dal') },
      { id: 11, name: 'Chawal', category: 'Main Course', price: 119.0, stock: 20, image_url: makeDishArtDataUri('Chawal') },
      { id: 12, name: 'Dal Chawal', category: 'Main Course', price: 179.0, stock: 16, image_url: makeDishArtDataUri('Dal Chawal') },
      { id: 13, name: 'Buttermilk', category: 'Beverages', price: 69.0, stock: 20, image_url: makeDishArtDataUri('Buttermilk') },
      { id: 14, name: 'Mango Shake', category: 'Beverages', price: 109.0, stock: 18, image_url: makeDishArtDataUri('Mango Shake') },
      { id: 15, name: 'Lassi', category: 'Beverages', price: 89.0, stock: 17, image_url: makeDishArtDataUri('Lassi') },
      { id: 16, name: 'Nachos', category: 'Appetizer', price: 169.0, stock: 11, image_url: makeDishArtDataUri('Nachos') }
    ];
  }

  renderCategoryFilters();
  renderMenu();
  updateDashboardStats();
}

// Load bookings from the API and redraw the booking list.
async function loadReservations() {
  try {
    const response = await fetch('/api/reservations');
    if (!response.ok) throw new Error('Failed to load reservations');
    const data = await response.json();
    reservationList = data.map((reservation) => ({
      id: reservation.id,
      name: reservation.guest_name,
      date: reservation.reservation_date,
      time: reservation.reservation_time,
      guests: reservation.guests
    }));
  } catch (error) {
    console.warn('Using fallback reservations:', error);
    reservationList = [
      { id: 1, name: 'Mila Parker', date: '2026-09-24', time: '19:30', guests: 4 },
      { id: 2, name: 'James Cole', date: '2026-09-24', time: '20:00', guests: 2 },
      { id: 3, name: 'Nora Chen', date: '2026-09-25', time: '18:45', guests: 6 }
    ];
  }

  renderReservations();
}

// Render menu filters and cards from the currently loaded menu data.
function uniqueCategories() {
  return ['All', ...new Set(menuItems.map((item) => item.category))];
}

function renderCategoryFilters() {
  categoryFilters.innerHTML = uniqueCategories()
    .map(
      (category) => `
        <button class="filter-pill ${category === currentCategory ? 'active' : ''}" data-category="${category}">
          ${category}
        </button>
      `
    )
    .join('');

  document.querySelectorAll('.filter-pill').forEach((button) => {
    button.addEventListener('click', () => {
      currentCategory = button.dataset.category;
      renderCategoryFilters();
      renderMenu();
    });
  });
}

function renderMenu() {
  const query = (menuSearch?.value || '').trim().toLowerCase();
  const visibleItems = menuItems.filter((item) => {
    const matchesCategory = currentCategory === 'All' || item.category === currentCategory;
    const matchesSearch = !query || [item.name, item.category].some((value) => (value || '').toLowerCase().includes(query));
    return matchesCategory && matchesSearch;
  });

  menuList.innerHTML = visibleItems
    .map(
      (item) => `
        <article class="menu-item">
          <img class="menu-item-image" src="${normaliseImageUrl(item)}" alt="${item.name}" />
          <div class="menu-item-top">
            <h4>${item.name}</h4>
            <span class="badge">${item.stock} left</span>
          </div>
          <p class="item-category">${item.category}</p>
          <p class="item-price">${money.format(item.price)}</p>
          <button data-add-item="${item.id}">Add to order</button>
        </article>
      `
    )
    .join('');

  if (!visibleItems.length) {
    menuList.innerHTML = '<p class="empty-state">No menu items match your search.</p>';
  }

  document.querySelectorAll('[data-add-item]').forEach((button) => {
    button.addEventListener('click', () => {
      button.classList.remove('pulse');
      void button.offsetWidth;
      button.classList.add('pulse');
      setTimeout(() => button.classList.remove('pulse'), 350);
      addToCart(Number(button.dataset.addItem));
    });
  });
}

// Cart helpers keep quantities, line totals, and displayed order totals in sync.
function addToCart(itemId) {
  const item = menuItems.find((menuItem) => menuItem.id === itemId);
  if (!item) return;

  const existing = cart.find((entry) => entry.id === itemId);
  if (existing) {
    existing.qty += 1;
  } else {
    cart.push({ id: itemId, name: item.name, price: item.price, qty: 1 });
  }

  renderCart();
}

function updateCartItem(itemId, change) {
  const item = cart.find((entry) => entry.id === itemId);
  if (!item) return;

  item.qty += change;
  if (item.qty <= 0) {
    cart = cart.filter((entry) => entry.id !== itemId);
  }

  renderCart();
}

function renderCart() {
  if (!cart.length) {
    orderItems.innerHTML = '<p class="empty-state">No items in the current order yet.</p>';
  } else {
    orderItems.innerHTML = cart
      .map(
        (item) => `
          <div class="order-item">
            <div>
              <h4>${item.name}</h4>
              <div class="qty-controls">
                <button data-decrease="${item.id}">-</button>
                <span>${item.qty}</span>
                <button data-increase="${item.id}">+</button>
              </div>
            </div>
            <div class="item-row">
              <strong>${money.format(item.price * item.qty)}</strong>
              <button class="remove-item" data-remove="${item.id}">Remove</button>
            </div>
          </div>
        `
      )
      .join('');
  }

  document.querySelectorAll('[data-increase]').forEach((button) => {
    button.addEventListener('click', () => updateCartItem(Number(button.dataset.increase), 1));
  });

  document.querySelectorAll('[data-decrease]').forEach((button) => {
    button.addEventListener('click', () => updateCartItem(Number(button.dataset.decrease), -1));
  });

  document.querySelectorAll('[data-remove]').forEach((button) => {
    button.addEventListener('click', () => updateCartItem(Number(button.dataset.remove), -999));
  });

  updateTotals();
}

function updateTotals() {
  const subtotal = cart.reduce((sum, item) => sum + item.price * item.qty, 0);
  const service = subtotal * 0.1;
  const total = subtotal + service;

  subtotalValue.textContent = money.format(subtotal);
  serviceValue.textContent = money.format(service);
  totalValue.textContent = money.format(total);

  const hasItems = cart.length > 0;
  placeOrderBtn.disabled = !hasItems;
  placeOrderBtn.textContent = hasItems ? 'Place order' : 'Add items first';
}

// Dashboard panels summarize menu, orders, reservations, staff, and kitchen state.
function renderPopularItems() {
  const rankedItems = [...menuItems].sort((a, b) => b.stock - a.stock).slice(0, 4);

  popularItems.innerHTML = rankedItems
    .map(
      (item, index) => `
        <div class="bar-row">
          <span class="bar-label">${item.name}</span>
          <div class="bar-track">
            <span class="bar-fill" style="width: ${(index + 1) * 26}%"></span>
          </div>
          <strong>${Math.max(24, ((index + 1) * 30))}%</strong>
        </div>
      `
    )
    .join('');
}

function renderRecentOrders() {
  recentOrdersBox.innerHTML = recentOrders
    .map(
      (order) => `
        <div class="order-feed-item">
          <div>
            <strong>${order.id}</strong>
            <div class="feed-meta">${order.table}</div>
          </div>
          <div>
            <strong>${money.format(order.total)}</strong>
            <div class="feed-meta">${order.status}</div>
          </div>
        </div>
      `
    )
    .join('');
}

function renderReservations() {
  reservationListBox.innerHTML = reservationList
    .map(
      (reservation) => `
        <div class="reservation-item">
          <div>
            <strong>${reservation.name}</strong>
            <span>${reservation.guests} guests</span>
          </div>
          <div>
            <span>${reservation.date}</span>
            <strong>${reservation.time}</strong>
          </div>
        </div>
      `
    )
    .join('');
}

function renderStaff() {
  staffList.innerHTML = staffMembers
    .map(
      (member) => `
        <div class="staff-item">
          <div class="staff-info">
            <strong>${member.name}</strong>
            <span>${member.role}</span>
          </div>
          <strong>${member.score}%</strong>
        </div>
      `
    )
    .join('');
}

function renderKitchenStatus() {
  kitchenStatusBox.innerHTML = kitchenStatus
    .map(
      (item) => `
        <div class="status-item">
          <span><i class="status-dot ${item.state}"></i>${item.label}</span>
          <strong>${item.value}</strong>
        </div>
      `
    )
    .join('');
}

function updateDashboardStats() {
  const totalSales = recentOrders.reduce((sum, order) => sum + order.total, 0);
  const ordersNumber = recentOrders.length + cart.length;
  const guestTotal = 128 + Math.round(totalSales / 7);
  const lowStockCount = menuItems.filter((item) => item.stock < 10).length;

  salesValue.textContent = money.format(totalSales + cart.reduce((sum, item) => sum + item.price * item.qty, 0));
  orderCount.textContent = String(ordersNumber);
  guestCount.textContent = String(guestTotal);
  alertCount.textContent = String(lowStockCount);
}

// Wire dashboard navigation and sign-out controls.
function attachNavigation() {
  document.querySelectorAll('.nav-item').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');

      document.querySelectorAll('.panel-section').forEach((section) => {
        section.classList.toggle('active-panel', section.id === button.dataset.section);
      });
    });
  });
}

function attachLogout() {
  const logoutButton = document.getElementById('logoutButton');
  if (!logoutButton) return;

  logoutButton.addEventListener('click', async () => {
    try {
      const response = await fetch('/api/logout', {
        method: 'POST'
      });

      if (response.ok) {
        window.location.href = '/login';
      }
    } catch (error) {
      console.error('Logout failed:', error);
      window.location.href = '/login';
    }
  });
}

// Populate the menu editor and keep the chosen item selected after saving.
function populateMenuEditSelect(selectedItemId = null) {
  if (!menuEditSelect) return;

  menuEditSelect.innerHTML = menuItems
    .map(
      (item) => `<option value="${item.id}">${item.name}</option>`
    )
    .join('');

  if (menuItems.length) {
    populateMenuEditForm(selectedItemId ?? menuItems[0].id);
  }
}

function populateMenuEditForm(itemId) {
  if (!menuEditSelect || !menuEditName || !menuEditCategory || !menuEditPrice || !menuEditStock || !menuEditImageUrl) return;

  const item = menuItems.find((menuItem) => menuItem.id === Number(itemId));
  if (!item) return;

  menuEditSelect.value = String(item.id);
  menuEditName.value = item.name || '';
  menuEditCategory.value = item.category || '';
  menuEditPrice.value = item.price ?? '';
  menuEditStock.value = item.stock ?? 0;
  menuEditImageUrl.value = item.image_url || '';
}

function attachMenuSearch() {
  if (!menuSearch) return;

  menuSearch.addEventListener('input', () => {
    renderMenu();
  });
}

function attachMenuEditForm() {
  if (!menuEditForm) return;

  if (menuImageUpload) {
    menuImageUpload.addEventListener('change', async (event) => {
      const file = event.target.files && event.target.files[0];
      if (!file) return;

      try {
        const dataUrl = await readLocalImageAsDataUrl(file);
        menuEditImageUrl.value = dataUrl;
        window.alert('Local photo selected and ready to save.');
      } catch (error) {
        window.alert(error.message || 'Unable to read the selected photo.');
      }
    });
  }

  menuEditSelect.addEventListener('change', (event) => {
    populateMenuEditForm(event.target.value);
  });

  menuEditForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const itemId = Number(menuEditSelect.value);
    const selectedItem = menuItems.find((item) => item.id === itemId);
    if (!selectedItem) return;

    const payload = {
      id: itemId,
      name: menuEditName.value.trim(),
      category: menuEditCategory.value.trim() || selectedItem.category,
      price: Number(menuEditPrice.value),
      stock: Number(menuEditStock.value),
      image_url: (menuEditImageUrl.value || '').trim(),
    };

    if (!payload.image_url) {
      payload.image_url = selectedItem.image_url || '';
    }

    try {
      const response = await fetch('/api/menu', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || 'Unable to update menu item.');
      }

      const index = menuItems.findIndex((item) => item.id === itemId);
      if (index >= 0) {
        menuItems[index] = {
          ...menuItems[index],
          ...data,
          image_url: data.image_url || menuItems[index].image_url,
        };
      }

      renderCategoryFilters();
      renderMenu();
      populateMenuEditSelect(itemId);
      if (menuImageUpload) {
        menuImageUpload.value = '';
      }
      window.alert('Menu item updated successfully.');
    } catch (error) {
      window.alert(error.message || 'Unable to update menu item.');
    }
  });
}

// Submit reservations and orders to the server, then refresh visible data.
function attachReservationForm() {
  document.getElementById('reservationForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const guestName = document.getElementById('guestName').value.trim();
    const reservationDate = document.getElementById('reservationDate').value;
    const reservationTime = document.getElementById('reservationTime').value;
    const guests = Number(document.getElementById('reservationGuests').value);

    if (!guestName || !reservationDate || !reservationTime || !guests) return;

    try {
      const response = await fetch('/api/reservations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          guest_name: guestName,
          reservation_date: reservationDate,
          reservation_time: reservationTime,
          guests
        })
      });

      if (!response.ok) {
        throw new Error('Unable to save reservation');
      }

      event.target.reset();
      await loadReservations();
    } catch (error) {
      console.error(error);
    }
  });
}

function attachOrderActions() {
  tableSelect.addEventListener('change', (event) => {
    const selected = event.target.value;
    tableLabel.textContent = selected;
  });

  placeOrderBtn.addEventListener('click', async () => {
    if (!cart.length) {
      window.alert('Please add at least one item to the order before placing it.');
      return;
    }

    placeOrderBtn.disabled = true;
    placeOrderBtn.textContent = 'Placing...';

    try {
      const payload = {
        items: cart.map((item) => ({ name: item.name, quantity: item.qty })),
        table_name: tableSelect.value,
        customer_name: customerName.value.trim() || 'Walk-in Customer',
        customer_phone: customerPhone.value.trim(),
        customer_email: customerEmail.value.trim(),
        customer_address: customerAddress.value.trim(),
        payment_method: paymentMethod.value,
        payment_status: paymentStatus.value
      };

      const response = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Unable to place order');
      }

      const result = await response.json();
      const table = tableSelect.value;
      const orderId = '#10' + (recentOrders.length + 80);

      recentOrders.unshift({
        id: orderId,
        total: result.total,
        table,
        status: result.payment_status === 'paid' ? 'Paid' : 'Preparing'
      });

      cart = [];
      customerName.value = '';
      customerPhone.value = '';
      customerEmail.value = '';
      customerAddress.value = '';
      renderCart();
      renderRecentOrders();
      updateDashboardStats();
      await loadMenu();
      window.alert(`Order placed successfully for ${table}. Total: ${money.format(result.total)}`);
    } catch (error) {
      console.error(error);
      window.alert(error.message || 'Unable to place order');
    } finally {
      placeOrderBtn.disabled = cart.length === 0;
      placeOrderBtn.textContent = cart.length === 0 ? 'Add items first' : 'Place order';
    }
  });
}

// Load initial data before attaching interaction handlers.
async function initialize() {
  await loadMenu();
  await loadReservations();
  renderCart();
  renderPopularItems();
  renderRecentOrders();
  renderStaff();
  renderKitchenStatus();
  updateDashboardStats();
  populateMenuEditSelect();
  attachNavigation();
  attachLogout();
  attachMenuSearch();
  attachMenuEditForm();
  attachReservationForm();
  attachOrderActions();
}

initialize();
