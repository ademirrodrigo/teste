const API_BASE = '';
let token = null;
let currentUser = null;
let selectedCompany = null;

async function apiRequest(path, options = {}) {
  if (!options.headers) {
    options.headers = {};
  }
  if (token) {
    options.headers['Authorization'] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData)) {
    options.headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || detail.message || 'Algo deu errado.');
  }
  if (response.status === 204) {
    return null;
  }
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response;
}

function formatCurrency(value) {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function toggleView(isLogged) {
  document.getElementById('login-section').classList.toggle('hidden', isLogged);
  document.getElementById('dashboard').classList.toggle('hidden', !isLogged);
}

async function loadHighlights() {
  const highlights = await apiRequest('/dashboard/overview');
  const container = document.getElementById('highlights');
  container.innerHTML = '';
  highlights.forEach((highlight) => {
    const div = document.createElement('div');
    div.className = 'highlight-card';
    div.innerHTML = `
      <span class="title">${highlight.title}</span>
      <span class="value">${highlight.value}</span>
      <span class="description">${highlight.description}</span>
    `;
    container.appendChild(div);
  });
}

async function loadFinancialReport() {
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth() - 2, 1);
  const end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  const startStr = start.toISOString().split('T')[0];
  const endStr = end.toISOString().split('T')[0];

  let companyId = selectedCompany;
  if (!companyId && currentUser && currentUser.company_id) {
    companyId = currentUser.company_id;
  }
  if (!companyId) {
    const companies = await apiRequest('/companies');
    if (companies.length) {
      companyId = companies[0].id;
      selectedCompany = companyId;
    } else {
      document.getElementById('period').textContent = 'Cadastre uma empresa para liberar os relatórios.';
      document.getElementById('dre-message').textContent = '';
      document.getElementById('dre-values').innerHTML = '';
      document.querySelector('#cashflow-table tbody').innerHTML = '';
      return;
    }
  }
  const report = await apiRequest(
    `/reports/financial-health?company_id=${companyId}&start_date=${startStr}&end_date=${endStr}`
  );

  document.getElementById('period').textContent = report.period;
  document.getElementById('dre-message').textContent = report.dre.message;
  const dreValues = document.getElementById('dre-values');
  dreValues.innerHTML = '';
  ['revenue', 'expenses', 'result'].forEach((key) => {
    const li = document.createElement('li');
    const label = key === 'revenue' ? 'Entradas' : key === 'expenses' ? 'Saídas' : 'Resultado';
    li.textContent = `${label}: ${formatCurrency(report.dre[key])}`;
    dreValues.appendChild(li);
  });

  const tbody = document.querySelector('#cashflow-table tbody');
  tbody.innerHTML = '';
  report.cash_flow.forEach((entry) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${entry.label}</td>
      <td>${formatCurrency(entry.inflow)}</td>
      <td>${formatCurrency(entry.outflow)}</td>
      <td>${formatCurrency(entry.balance)}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const errorElement = document.getElementById('login-error');
  errorElement.textContent = '';
  try {
    const response = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    token = response.access_token;
    currentUser = await apiRequest('/auth/me');
    document.getElementById('welcome').textContent = `Olá, ${currentUser.full_name}!`;
    toggleView(true);
    await loadHighlights();
    await loadFinancialReport();
  } catch (error) {
    errorElement.textContent = error.message;
  }
}

function handleLogout() {
  token = null;
  currentUser = null;
  selectedCompany = null;
  document.getElementById('login-form').reset();
  toggleView(false);
}

async function handleExport() {
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth() - 2, 1);
  const end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  const startStr = start.toISOString().split('T')[0];
  const endStr = end.toISOString().split('T')[0];
  let companyId = selectedCompany || (currentUser ? currentUser.company_id : null);
  if (!companyId) {
    const companies = await apiRequest('/companies');
    if (companies.length) {
      companyId = companies[0].id;
    }
  }
  if (!companyId) {
    alert('Cadastre uma empresa para gerar o relatório.');
    return;
  }
  const format = document.getElementById('export-format').value;
  const response = await apiRequest(
    `/reports/export?company_id=${companyId}&start_date=${startStr}&end_date=${endStr}&export_format=${format}`,
    { method: 'GET' }
  );
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `relatorio-${format}.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('login-form').addEventListener('submit', handleLogin);
  document.getElementById('logout').addEventListener('click', handleLogout);
  document.getElementById('export-report').addEventListener('click', handleExport);
});
