const API_BASE = '';
let token = null;
let currentUser = null;
let selectedCompany = null;
let periodPreset = '90';
let cashflowChart = null;

const PERIOD_PRESETS = {
  '30': {
    label: 'Últimos 30 dias',
    compute() {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 29);
      return { start, end };
    }
  },
  '90': {
    label: 'Últimos 90 dias',
    compute() {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 89);
      return { start, end };
    }
  },
  '180': {
    label: 'Últimos 6 meses',
    compute() {
      const end = new Date();
      const start = new Date();
      start.setMonth(end.getMonth() - 5);
      start.setDate(1);
      return { start, end };
    }
  },
  '365': {
    label: 'Últimos 12 meses',
    compute() {
      const end = new Date();
      const start = new Date();
      start.setFullYear(end.getFullYear() - 1);
      start.setDate(end.getDate() + 1);
      return { start, end };
    }
  }
};

async function apiRequest(path, options = {}) {
  const config = { ...options };
  config.headers = config.headers ? { ...config.headers } : {};
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  const isForm = config.body instanceof FormData;
  if (!isForm && !config.headers['Content-Type'] && config.method && config.method !== 'GET') {
    config.headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(`${API_BASE}${path}`, config);
  if (!response.ok) {
    if (response.status === 401) {
      handleLogout();
    }
    let detail = 'Algo deu errado.';
    try {
      const data = await response.json();
      detail = data.detail || data.message || detail;
    } catch (error) {
      // ignore JSON parse errors
    }
    throw new Error(detail);
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
  return Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDate(isoDate) {
  const date = new Date(isoDate);
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
}

function toggleView(isLogged) {
  document.getElementById('login-section').classList.toggle('hidden', isLogged);
  document.getElementById('dashboard').classList.toggle('hidden', !isLogged);
  document.getElementById('top-actions').classList.toggle('hidden', !isLogged);
}

function updatePeriodButtons(rangeKey) {
  document.querySelectorAll('.period-selector .chip').forEach((chip) => {
    chip.classList.toggle('active', chip.dataset.range === rangeKey);
  });
}

function computePeriodRange(rangeKey) {
  const preset = PERIOD_PRESETS[rangeKey] || PERIOD_PRESETS['90'];
  const { start, end } = preset.compute();
  const normalizedStart = new Date(Date.UTC(start.getFullYear(), start.getMonth(), start.getDate()));
  const normalizedEnd = new Date(Date.UTC(end.getFullYear(), end.getMonth(), end.getDate()));
  return {
    start: normalizedStart.toISOString().split('T')[0],
    end: normalizedEnd.toISOString().split('T')[0]
  };
}

async function loadHighlights() {
  const highlights = await apiRequest('/dashboard/overview');
  const container = document.getElementById('highlights');
  container.innerHTML = '';
  if (!highlights.length) {
    container.innerHTML = '<p class="muted">Cadastre empresas e lançamentos para liberar os destaques.</p>';
    return;
  }
  highlights.forEach((highlight) => {
    const card = document.createElement('div');
    card.className = 'highlight-card';
    const numericValue = Number(highlight.value.replace(/[^0-9,-]/g, '').replace(',', '.'));
    if (!Number.isNaN(numericValue)) {
      card.classList.add(numericValue >= 0 ? 'positive' : 'negative');
    }
    card.innerHTML = `
      <span class="title">${highlight.title}</span>
      <span class="value">${highlight.value}</span>
      <span class="description">${highlight.description}</span>
    `;
    container.appendChild(card);
  });
}

function renderOutstanding(listId, items, type) {
  const list = document.getElementById(listId);
  list.innerHTML = '';
  if (!items.length) {
    const empty = document.createElement('li');
    empty.className = 'empty-state';
    empty.textContent = type === 'receivables'
      ? 'Sem entradas previstas no período selecionado.'
      : 'Sem pagamentos pendentes no período selecionado.';
    list.appendChild(empty);
    return;
  }
  items.slice(0, 6).forEach((item) => {
    const li = document.createElement('li');
    li.className = `status-item ${type === 'receivables' ? 'positive' : 'negative'}`;
    li.innerHTML = `
      <div class="status-meta">
        <span>${item.description}</span>
        <span class="status-date">Para ${formatDate(item.due_date)}</span>
      </div>
      <div class="status-info">
        <span class="status-chip">${type === 'receivables' ? 'Entrada' : 'Saída'}</span>
        <span class="status-amount">${formatCurrency(item.amount)}</span>
      </div>
    `;
    list.appendChild(li);
  });
}

function renderCashflowTable(entries) {
  const tbody = document.querySelector('#cashflow-table tbody');
  tbody.innerHTML = '';
  entries.forEach((entry) => {
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

function renderCashflowChart(entries) {
  const ctx = document.getElementById('cashflow-chart').getContext('2d');
  const labels = entries.map((entry) => entry.label);
  const inflow = entries.map((entry) => entry.inflow);
  const outflow = entries.map((entry) => entry.outflow);
  const balance = entries.map((entry) => entry.balance);

  if (cashflowChart) {
    cashflowChart.data.labels = labels;
    cashflowChart.data.datasets[0].data = inflow;
    cashflowChart.data.datasets[1].data = outflow;
    cashflowChart.data.datasets[2].data = balance;
    cashflowChart.update();
    return;
  }

  cashflowChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Entradas',
          data: inflow,
          borderColor: '#3cb7a0',
          backgroundColor: 'rgba(60, 183, 160, 0.25)',
          tension: 0.35,
          fill: true,
          borderWidth: 3
        },
        {
          label: 'Saídas',
          data: outflow,
          borderColor: '#d64045',
          backgroundColor: 'rgba(214, 64, 69, 0.12)',
          tension: 0.35,
          fill: true,
          borderWidth: 3
        },
        {
          label: 'Saldo acumulado',
          data: balance,
          borderColor: '#1f7a8c',
          backgroundColor: 'rgba(31, 122, 140, 0.18)',
          tension: 0.25,
          fill: false,
          borderDash: [6, 6],
          borderWidth: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          ticks: {
            callback: (value) => formatCurrency(value)
          }
        }
      },
      plugins: {
        legend: {
          display: true
        },
        tooltip: {
          callbacks: {
            label(context) {
              return `${context.dataset.label}: ${formatCurrency(context.parsed.y)}`;
            }
          }
        }
      }
    }
  });
}

async function loadFinancialReport() {
  if (!currentUser) {
    return;
  }
  const { start, end } = computePeriodRange(periodPreset);

  let companyId = selectedCompany;
  if (!companyId && currentUser.company_id) {
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
      document.getElementById('receivables-list').innerHTML = '';
      document.getElementById('payables-list').innerHTML = '';
      return;
    }
  }

  const report = await apiRequest(
    `/reports/financial-health?company_id=${companyId}&start_date=${start}&end_date=${end}`
  );

  document.getElementById('period').textContent = report.period;
  document.getElementById('dre-message').textContent = report.dre.message;

  const dreValues = document.getElementById('dre-values');
  dreValues.innerHTML = '';
  const dreLabels = [
    { key: 'revenue', label: 'Entradas' },
    { key: 'expenses', label: 'Saídas' },
    { key: 'result', label: 'Resultado' }
  ];
  dreLabels.forEach(({ key, label }) => {
    const li = document.createElement('li');
    li.textContent = `${label}: ${formatCurrency(report.dre[key])}`;
    dreValues.appendChild(li);
  });

  renderCashflowTable(report.cash_flow);
  renderCashflowChart(report.cash_flow);
  renderOutstanding('receivables-list', report.receivables, 'receivables');
  renderOutstanding('payables-list', report.payables, 'payables');
}

async function populateCompanies() {
  const selectContainer = document.getElementById('company-selector');
  const select = document.getElementById('company-picker');
  if (!currentUser) {
    selectContainer.classList.add('hidden');
    return;
  }

  const companies = await apiRequest('/companies');
  if (currentUser.role === 'client' || companies.length <= 1) {
    selectContainer.classList.add('hidden');
    if (currentUser.role === 'client') {
      selectedCompany = currentUser.company_id;
    } else if (companies.length === 1) {
      selectedCompany = companies[0].id;
    }
    return;
  }

  selectContainer.classList.remove('hidden');
  select.innerHTML = '';
  companies.forEach((company) => {
    const option = document.createElement('option');
    option.value = company.id;
    option.textContent = company.name;
    if (!selectedCompany) {
      selectedCompany = company.id;
    }
    if (Number(selectedCompany) === company.id) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById('email').value.trim();
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
    await populateCompanies();
    updatePeriodButtons(periodPreset);
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
  periodPreset = '90';
  if (cashflowChart) {
    cashflowChart.destroy();
    cashflowChart = null;
  }
  document.getElementById('login-form').reset();
  updatePeriodButtons(periodPreset);
  toggleView(false);
}

async function handleExport() {
  if (!currentUser) {
    return;
  }
  const { start, end } = computePeriodRange(periodPreset);
  let companyId = selectedCompany || currentUser.company_id;
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
    `/reports/export?company_id=${companyId}&start_date=${start}&end_date=${end}&export_format=${format}`,
    { method: 'GET' }
  );
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `relatorio-${format}.${format}`;
  a.click();
  window.URL.revokeObjectURL(url);
}

function handlePeriodChange(event) {
  const button = event.target.closest('button[data-range]');
  if (!button) {
    return;
  }
  const { range } = button.dataset;
  if (range === periodPreset) {
    return;
  }
  periodPreset = range;
  updatePeriodButtons(range);
  loadFinancialReport();
}

function handleQuickExport() {
  document.getElementById('export-report').click();
}

function registerEventListeners() {
  document.getElementById('login-form').addEventListener('submit', handleLogin);
  document.getElementById('logout').addEventListener('click', handleLogout);
  document.getElementById('export-report').addEventListener('click', handleExport);
  document.getElementById('quick-export').addEventListener('click', handleQuickExport);
  document.querySelector('.period-selector').addEventListener('click', handlePeriodChange);
  document.getElementById('company-picker').addEventListener('change', (event) => {
    const value = event.target.value;
    selectedCompany = value ? Number(value) : null;
    loadFinancialReport();
  });
}

window.addEventListener('DOMContentLoaded', () => {
  registerEventListeners();
  updatePeriodButtons(periodPreset);
});
