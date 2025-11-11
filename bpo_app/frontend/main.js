const API_BASE = '';
let token = null;
let currentUser = null;
let selectedCompany = null;
let periodPreset = '90';
let cashflowChart = null;
let cachedCompanies = [];
let cachedUsers = [];
let cachedAccounts = [];
let cachedCategories = [];
let cachedTransactions = [];
let cachedGoals = [];
let cachedTasks = [];
let cachedGoalSummary = null;
let cachedTaskSummary = null;
let configCompanyId = null;
let currentConfigTab = 'overview';
let editingCompanyId = null;
let editingUserId = null;
let editingGoalId = null;
let editingTaskId = null;

const ROLE_LABELS = {
  admin: 'Administrador',
  staff: 'Equipe interna',
  client: 'Cliente'
};

const GOAL_DIRECTION_LABELS = {
  inflow: 'Entradas',
  outflow: 'Saídas'
};

const GOAL_STATUS_LABELS = {
  in_progress: 'Em andamento',
  achieved: 'Concluída',
  missed: 'Ajustar meta'
};

const TASK_STATUS_LABELS = {
  open: 'Aberta',
  in_progress: 'Em andamento',
  done: 'Concluída'
};

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

function setFeedback(elementId, message, isError = false) {
  const element = document.getElementById(elementId);
  if (!element) {
    return;
  }
  element.textContent = message;
  element.classList.toggle('success', Boolean(message) && !isError);
  element.classList.toggle('error', Boolean(message) && isError);
}

function clearFeedback(elementId) {
  setFeedback(elementId, '');
}

function normalizeStringValue(value) {
  if (value === undefined || value === null) {
    return null;
  }
  const cleaned = String(value).trim();
  return cleaned ? cleaned : null;
}

function isAdminOrStaff() {
  return currentUser && (currentUser.role === 'admin' || currentUser.role === 'staff');
}

function getActiveCompanyId() {
  if (!currentUser) {
    return null;
  }
  if (currentUser.role === 'client') {
    return currentUser.company_id || null;
  }
  return configCompanyId || selectedCompany || null;
}

function toggleCompanyDependentForms(disabled) {
  const ids = [
    'config-account-form',
    'config-category-form',
    'config-transaction-form',
    'config-import-form',
    'config-goal-form',
    'config-task-form'
  ];
  ids.forEach((formId) => {
    const form = document.getElementById(formId);
    if (!form) {
      return;
    }
    form.classList.toggle('disabled', disabled);
    Array.from(form.querySelectorAll('input, select, textarea, button')).forEach((element) => {
      element.disabled = disabled;
    });
  });
}

function updateMetricValue(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function updateGoalMetrics(summary) {
  const total = summary?.total ?? 0;
  const archived = summary?.archived ?? 0;
  const active = Math.max(total - archived, 0);
  updateMetricValue('goal-metric-active', String(active));
  updateMetricValue('goal-metric-achieved', String(summary?.achieved ?? 0));
  updateMetricValue('goal-metric-missed', String(summary?.missed ?? 0));
  const nextElement = document.getElementById('goal-metric-next');
  if (nextElement) {
    if (summary?.next_deadline) {
      const nextDate = summary.next_deadline;
      const today = new Date();
      const isoToday = today.toISOString().slice(0, 10);
      if (nextDate === isoToday) {
        nextElement.textContent = 'Hoje';
      } else {
        nextElement.textContent = formatDate(nextDate);
      }
    } else {
      nextElement.textContent = '-';
    }
  }
}

function updateTaskMetrics(summary) {
  const open = summary?.open ?? 0;
  const inProgress = summary?.in_progress ?? 0;
  const pendingTotal = open + inProgress;
  updateMetricValue('task-metric-pending', String(pendingTotal));
  updateMetricValue('task-metric-in-progress', String(inProgress));
  updateMetricValue('task-metric-done', String(summary?.done ?? 0));
  updateMetricValue('task-metric-overdue', String(summary?.overdue ?? 0));
  updateMetricValue('task-metric-today', String(summary?.due_today ?? 0));
}

function populateTransactionAccountOptions() {
  const select = document.getElementById('config-transaction-account');
  if (!select) {
    return;
  }
  select.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Sem conta específica';
  select.appendChild(placeholder);
  cachedAccounts.forEach((account) => {
    const option = document.createElement('option');
    option.value = account.id;
    option.textContent = account.name;
    select.appendChild(option);
  });
}

function populateTransactionCategoryOptions() {
  const select = document.getElementById('config-transaction-category');
  if (!select) {
    return;
  }
  select.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Sem categoria';
  select.appendChild(placeholder);
  cachedCategories.forEach((category) => {
    const option = document.createElement('option');
    option.value = category.id;
    option.textContent = category.name;
    select.appendChild(option);
  });
}

function populateUserCompanySelect() {
  const select = document.getElementById('config-user-company');
  if (!select) {
    return;
  }
  select.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Sem vínculo (somente equipe)';
  select.appendChild(placeholder);
  cachedCompanies.forEach((company) => {
    const option = document.createElement('option');
    option.value = company.id;
    option.textContent = company.name;
    select.appendChild(option);
  });
  if (configCompanyId) {
    select.value = String(configCompanyId);
  }
}

function populateTaskAssigneeSelect() {
  const select = document.getElementById('config-task-owner');
  if (!select) {
    return;
  }
  select.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Sem responsável definido';
  select.appendChild(placeholder);

  let options = [];
  if (isAdminOrStaff()) {
    options = cachedUsers.filter((user) => user.is_active !== false);
  } else if (currentUser) {
    options = [currentUser];
  }

  options.forEach((user) => {
    const option = document.createElement('option');
    option.value = user.id;
    const companyName = user.company_id
      ? cachedCompanies.find((company) => company.id === user.company_id)?.name
      : null;
    option.textContent = companyName ? `${user.full_name} · ${companyName}` : user.full_name;
    select.appendChild(option);
  });
}

function populateConfigFocusSelect() {
  const wrapper = document.getElementById('config-focus');
  const select = document.getElementById('config-company-focus');
  if (!wrapper || !select) {
    return;
  }
  const hasCompanies = cachedCompanies.length > 0;
  wrapper.classList.toggle('hidden', currentUser?.role === 'client');
  select.innerHTML = '';
  if (!hasCompanies) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'Cadastre uma empresa para começar';
    select.appendChild(option);
    select.disabled = true;
    toggleCompanyDependentForms(true);
    return;
  }
  select.disabled = currentUser?.role === 'client';
  cachedCompanies.forEach((company) => {
    const option = document.createElement('option');
    option.value = company.id;
    option.textContent = company.name;
    select.appendChild(option);
  });
  const fallbackCompany =
    configCompanyId && cachedCompanies.some((company) => company.id === Number(configCompanyId))
      ? Number(configCompanyId)
      : currentUser?.role === 'client'
        ? currentUser.company_id
        : cachedCompanies[0]?.id;
  configCompanyId = fallbackCompany ? Number(fallbackCompany) : null;
  if (configCompanyId) {
    select.value = String(configCompanyId);
  } else {
    select.value = '';
  }
  toggleCompanyDependentForms(!configCompanyId);
  populateUserCompanySelect();
}

function updateConfigCounts() {
  const setCount = (id, value) => {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = String(value ?? 0);
    }
  };
  setCount('overview-companies-count', cachedCompanies.length);
  setCount('overview-users-count', cachedUsers.length);
  setCount('overview-accounts-count', cachedAccounts.length);
  setCount('overview-categories-count', cachedCategories.length);
  const activeGoals = cachedGoals.filter((item) => !item.goal.archived).length;
  const pendingTasks = cachedTasks.filter((task) => task.status !== 'done').length;
  setCount('overview-goals-count', activeGoals);
  setCount('overview-tasks-count', pendingTasks);
}

function updateConfigMenuVisibility() {
  const usersButton = document.querySelector('#config-menu button[data-tab="users"]');
  const usersPanel = document.querySelector('.config-panel[data-panel="users"]');
  const showUsers = isAdminOrStaff();
  if (usersButton) {
    usersButton.classList.toggle('hidden', !showUsers);
    if (!showUsers && currentConfigTab === 'users') {
      currentConfigTab = 'overview';
    }
  }
  if (usersPanel) {
    usersPanel.classList.toggle('hidden', !showUsers);
  }
}

function updateRoleBasedUI() {
  const configButton = document.getElementById('open-config');
  const showConfig = isAdminOrStaff();
  if (configButton) {
    configButton.classList.toggle('hidden', !showConfig);
  }
  if (currentUser?.role === 'client') {
    configCompanyId = currentUser.company_id || null;
  }
  updateConfigMenuVisibility();
  populateConfigFocusSelect();
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

async function fetchCompanies() {
  const companies = await apiRequest('/companies');
  cachedCompanies = companies;
  populateConfigFocusSelect();
  return companies;
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

function renderGoalSummary(summary) {
  const container = document.getElementById('goal-summary');
  if (!container) {
    return;
  }
  container.innerHTML = '';
  updateGoalMetrics(summary);
  if (!summary) {
    const empty = document.createElement('p');
    empty.className = 'muted small';
    empty.textContent = 'Cadastre metas para acompanhar objetivos financeiros aqui.';
    container.appendChild(empty);
    return;
  }
  const upcoming = summary.upcoming || [];
  if (!upcoming.length) {
    const message = document.createElement('p');
    message.className = 'muted small';
    if (summary.total === 0) {
      message.textContent = 'Cadastre metas para acompanhar objetivos financeiros aqui.';
    } else {
      message.textContent = 'Todas as metas estão concluídas ou arquivadas no momento.';
    }
    container.appendChild(message);
    return;
  }
  upcoming.forEach((item) => {
    const card = document.createElement('article');
    card.className = `goal-summary-card status-${item.status}`;
    const header = document.createElement('div');
    header.className = 'goal-summary-header';
    const title = document.createElement('strong');
    title.textContent = item.goal.name;
    header.appendChild(title);
    const direction = document.createElement('span');
    direction.className = 'goal-summary-direction';
    direction.textContent = GOAL_DIRECTION_LABELS[item.goal.direction] || item.goal.direction;
    header.appendChild(direction);
    card.appendChild(header);

    const statusLabel = document.createElement('span');
    statusLabel.className = `status-pill goal-summary-status status-${item.status}`;
    statusLabel.textContent = GOAL_STATUS_LABELS[item.status] || item.status;
    card.appendChild(statusLabel);

    const progressText = document.createElement('div');
    progressText.className = 'goal-summary-values';
    progressText.textContent = `${formatCurrency(item.actual_amount)} de ${formatCurrency(item.goal.target_amount)}`;
    card.appendChild(progressText);

    const bar = document.createElement('div');
    bar.className = 'goal-progress-bar';
    const fill = document.createElement('div');
    fill.style.width = `${Math.min(item.progress_percentage, 100)}%`;
    bar.appendChild(fill);
    card.appendChild(bar);

    const message = document.createElement('p');
    message.className = 'muted small';
    message.textContent = item.message;
    card.appendChild(message);

    container.appendChild(card);
  });

  const totalUpcoming = upcoming.length;
  const activeGoals = Math.max((summary.total ?? 0) - (summary.archived ?? 0), 0);
  if (activeGoals > totalUpcoming) {
    const hint = document.createElement('p');
    hint.className = 'muted small';
    hint.textContent = `+${activeGoals - totalUpcoming} metas disponíveis no centro de configurações.`;
    container.appendChild(hint);
  }
}

function renderTaskSummary(summary) {
  const list = document.getElementById('task-summary-list');
  const empty = document.getElementById('task-summary-empty');
  if (!list || !empty) {
    return;
  }
  list.innerHTML = '';
  updateTaskMetrics(summary);
  const tasks = summary?.spotlight ?? [];
  const pendingTotal = (summary?.open ?? 0) + (summary?.in_progress ?? 0);
  if (!tasks.length) {
    if ((summary?.total ?? 0) === 0) {
      empty.textContent = 'Cadastre tarefas para controlar entregas combinadas com o escritório.';
    } else {
      empty.textContent = 'Checklist em dia! Não há tarefas pendentes.';
    }
    return;
  }
  empty.textContent = '';
  tasks.slice(0, 4).forEach((task) => {
    const li = document.createElement('li');
    li.className = 'task-summary-item';

    const title = document.createElement('div');
    title.className = 'task-summary-title';
    const strong = document.createElement('strong');
    strong.textContent = task.title;
    title.appendChild(strong);
    if (task.description) {
      const desc = document.createElement('p');
      desc.className = 'muted small';
      desc.textContent = task.description;
      title.appendChild(desc);
    }
    li.appendChild(title);

    const meta = document.createElement('div');
    meta.className = 'task-summary-meta';
    const statusChip = document.createElement('span');
    statusChip.className = `task-summary-chip status-${task.status}`;
    statusChip.textContent = TASK_STATUS_LABELS[task.status] || task.status;
    meta.appendChild(statusChip);

    const dueInfo = document.createElement('span');
    dueInfo.className = 'task-summary-date';
    dueInfo.textContent = task.due_date ? `Até ${formatDate(task.due_date)}` : 'Sem prazo definido';
    meta.appendChild(dueInfo);

    const owner = document.createElement('span');
    owner.className = 'task-summary-owner';
    owner.textContent = task.assigned_to ? task.assigned_to.full_name : 'Sem responsável';
    meta.appendChild(owner);

    li.appendChild(meta);
    list.appendChild(li);
  });

  if (pendingTotal > 4) {
    const more = document.createElement('li');
    more.className = 'task-summary-more muted small';
    more.textContent = `+${pendingTotal - 4} tarefas aguardando atenção.`;
    list.appendChild(more);
  }
}

async function loadGoalSummary() {
  const container = document.getElementById('goal-summary');
  if (!container || !currentUser) {
    return;
  }
  let companyId = selectedCompany || currentUser.company_id || configCompanyId;
  if (isAdminOrStaff()) {
    if (!companyId && cachedCompanies.length) {
      companyId = cachedCompanies[0].id;
    }
  }
  if (!companyId) {
    cachedGoalSummary = null;
    updateGoalMetrics(null);
    container.innerHTML = '<p class="muted small">Cadastre uma empresa e metas financeiras para visualizar aqui.</p>';
    return;
  }
  try {
    const summary = await apiRequest(`/financial-goals/summary?company_id=${companyId}`);
    cachedGoalSummary = summary;
    renderGoalSummary(summary);
  } catch (error) {
    cachedGoalSummary = null;
    updateGoalMetrics(null);
    container.innerHTML = `<p class="muted small">${error.message}</p>`;
  }
}

async function loadTaskSummary() {
  const list = document.getElementById('task-summary-list');
  const empty = document.getElementById('task-summary-empty');
  if (!list || !empty || !currentUser) {
    return;
  }
  let companyId = selectedCompany || currentUser.company_id || configCompanyId;
  if (isAdminOrStaff()) {
    if (!companyId && cachedCompanies.length) {
      companyId = cachedCompanies[0].id;
    }
  }
  if (!companyId) {
    cachedTaskSummary = null;
    updateTaskMetrics(null);
    renderTaskSummary(null);
    return;
  }
  try {
    const summary = await apiRequest(`/tasks/summary?company_id=${companyId}`);
    cachedTaskSummary = summary;
    renderTaskSummary(summary);
  } catch (error) {
    cachedTaskSummary = null;
    updateTaskMetrics(null);
    empty.textContent = error.message;
  }
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

  const companies = await fetchCompanies();
  if (!companies.length) {
    selectContainer.classList.add('hidden');
    selectedCompany = null;
    return;
  }

  if (currentUser.role === 'client') {
    selectContainer.classList.add('hidden');
    selectedCompany = currentUser.company_id;
    configCompanyId = currentUser.company_id;
    return;
  }

  if (!selectedCompany || !companies.some((company) => company.id === Number(selectedCompany))) {
    selectedCompany = companies[0].id;
  }

  selectContainer.classList.toggle('hidden', companies.length <= 1);
  select.innerHTML = '';
  companies.forEach((company) => {
    const option = document.createElement('option');
    option.value = company.id;
    option.textContent = company.name;
    if (Number(selectedCompany) === company.id) {
      option.selected = true;
    }
    select.appendChild(option);
  });

  if (isAdminOrStaff() && !configCompanyId) {
    configCompanyId = Number(selectedCompany);
    populateConfigFocusSelect();
  }
}

function renderCompanyList(companies) {
  const list = document.getElementById('config-company-list');
  if (!list) {
    return;
  }
  list.innerHTML = '';
  if (!companies.length) {
    const empty = document.createElement('li');
    empty.className = 'empty-state';
    empty.textContent = 'Cadastre a primeira empresa para liberar os demais recursos.';
    list.appendChild(empty);
    return;
  }
  companies.forEach((company) => {
    const li = document.createElement('li');
    const meta = document.createElement('div');
    meta.className = 'item-meta';
    const title = document.createElement('strong');
    title.textContent = company.name;
    meta.appendChild(title);
    if (company.trade_name) {
      const trade = document.createElement('span');
      trade.className = 'muted';
      trade.textContent = company.trade_name;
      meta.appendChild(trade);
    }
    if (company.document) {
      const documentInfo = document.createElement('span');
      documentInfo.className = 'muted small';
      documentInfo.textContent = company.document;
      meta.appendChild(documentInfo);
    }
    li.appendChild(meta);

    if (isAdminOrStaff()) {
      const actions = document.createElement('div');
      actions.className = 'item-actions';
      const editButton = document.createElement('button');
      editButton.className = 'inline';
      editButton.dataset.action = 'edit';
      editButton.dataset.id = company.id;
      editButton.textContent = 'Editar';
      actions.appendChild(editButton);
      if (currentUser?.role === 'admin') {
        const deleteButton = document.createElement('button');
        deleteButton.className = 'inline';
        deleteButton.dataset.action = 'delete';
        deleteButton.dataset.id = company.id;
        deleteButton.textContent = 'Remover';
        actions.appendChild(deleteButton);
      }
      li.appendChild(actions);
    }

    list.appendChild(li);
  });
}

function resetCompanyForm() {
  const form = document.getElementById('config-company-form');
  if (!form) {
    return;
  }
  form.reset();
  editingCompanyId = null;
  const title = document.getElementById('config-company-form-title');
  if (title) {
    title.textContent = 'Nova empresa';
  }
  const cancelButton = document.getElementById('config-company-cancel');
  if (cancelButton) {
    cancelButton.classList.add('hidden');
  }
  clearFeedback('config-company-feedback');
}

function startCompanyEdit(companyId) {
  const company = cachedCompanies.find((item) => item.id === Number(companyId));
  if (!company) {
    return;
  }
  editingCompanyId = company.id;
  const title = document.getElementById('config-company-form-title');
  if (title) {
    title.textContent = 'Editar empresa';
  }
  const cancelButton = document.getElementById('config-company-cancel');
  if (cancelButton) {
    cancelButton.classList.remove('hidden');
  }
  document.getElementById('config-company-name').value = company.name || '';
  document.getElementById('config-company-trade').value = company.trade_name || '';
  document.getElementById('config-company-document').value = company.document || '';
  document.getElementById('config-company-notes').value = company.notes || '';
}

async function refreshCompaniesSection() {
  const companies = await fetchCompanies();
  renderCompanyList(companies);
  updateConfigCounts();
}

async function handleCompanySubmit(event) {
  event.preventDefault();
  const nameInput = document.getElementById('config-company-name');
  const payload = {
    name: nameInput.value.trim(),
    trade_name: normalizeStringValue(document.getElementById('config-company-trade').value),
    document: normalizeStringValue(document.getElementById('config-company-document').value),
    notes: normalizeStringValue(document.getElementById('config-company-notes').value)
  };
  if (!payload.name) {
    setFeedback('config-company-feedback', 'Informe o nome da empresa.', true);
    return;
  }
  const isEditing = Boolean(editingCompanyId);
  const url = isEditing ? `/companies/${editingCompanyId}` : '/companies';
  const method = isEditing ? 'PUT' : 'POST';
  try {
    const response = await apiRequest(url, {
      method,
      body: JSON.stringify(payload)
    });
    setFeedback(
      'config-company-feedback',
      isEditing ? 'Empresa atualizada com sucesso!' : 'Empresa cadastrada com sucesso!',
      false
    );
    if (!isEditing && response?.id) {
      configCompanyId = response.id;
    }
    await refreshCompaniesSection();
    await populateCompanies();
    await refreshAccountsSection();
    await refreshCategoriesSection();
    await refreshTransactionsSection();
    resetCompanyForm();
  } catch (error) {
    setFeedback('config-company-feedback', error.message, true);
  }
}

async function handleCompanyListClick(event) {
  const button = event.target.closest('button[data-action]');
  if (!button) {
    return;
  }
  const companyId = Number(button.dataset.id);
  if (button.dataset.action === 'edit') {
    startCompanyEdit(companyId);
    return;
  }
  if (button.dataset.action === 'delete') {
    const company = cachedCompanies.find((item) => item.id === companyId);
    if (!company) {
      return;
    }
    const confirmed = window.confirm(
      `Tem certeza de que deseja remover a empresa "${company.name}"? Esta ação não pode ser desfeita.`
    );
    if (!confirmed) {
      return;
    }
    try {
      await apiRequest(`/companies/${companyId}`, { method: 'DELETE' });
      setFeedback('config-company-feedback', 'Empresa removida.', false);
      if (configCompanyId === companyId) {
        configCompanyId = null;
      }
      await refreshCompaniesSection();
      await populateCompanies();
      await refreshAccountsSection();
      await refreshCategoriesSection();
      await refreshTransactionsSection();
    } catch (error) {
      setFeedback('config-company-feedback', error.message, true);
    }
  }
}

function renderUserList(users) {
  const list = document.getElementById('config-user-list');
  if (!list) {
    return;
  }
  list.innerHTML = '';
  if (!isAdminOrStaff()) {
    const info = document.createElement('li');
    info.className = 'empty-state';
    info.textContent = 'Somente o escritório pode gerenciar usuários.';
    list.appendChild(info);
    return;
  }
  if (!users.length) {
    const empty = document.createElement('li');
    empty.className = 'empty-state';
    empty.textContent = 'Nenhum usuário cadastrado ainda.';
    list.appendChild(empty);
    return;
  }
  users.forEach((user) => {
    const li = document.createElement('li');
    const meta = document.createElement('div');
    meta.className = 'item-meta';
    const title = document.createElement('strong');
    title.textContent = user.full_name;
    meta.appendChild(title);
    const email = document.createElement('span');
    email.className = 'muted';
    email.textContent = user.email;
    meta.appendChild(email);
    const companyName = user.company_id
      ? cachedCompanies.find((company) => company.id === user.company_id)?.name
      : null;
    const badge = document.createElement('span');
    badge.className = 'muted small';
    badge.textContent = `${ROLE_LABELS[user.role] || user.role}${companyName ? ` · ${companyName}` : ''}`;
    if (user.is_active === false) {
      badge.textContent += ' · Inativo';
    }
    meta.appendChild(badge);
    li.appendChild(meta);

    const actions = document.createElement('div');
    actions.className = 'item-actions';
    const editButton = document.createElement('button');
    editButton.className = 'inline';
    editButton.dataset.action = 'edit';
    editButton.dataset.id = user.id;
    editButton.textContent = 'Editar';
    actions.appendChild(editButton);
    li.appendChild(actions);

    list.appendChild(li);
  });
}

function resetUserForm() {
  const form = document.getElementById('config-user-form');
  if (!form) {
    return;
  }
  form.reset();
  editingUserId = null;
  document.getElementById('config-user-active').checked = true;
  const title = document.getElementById('config-user-form-title');
  if (title) {
    title.textContent = 'Novo usuário';
  }
  const cancelButton = document.getElementById('config-user-cancel');
  if (cancelButton) {
    cancelButton.classList.add('hidden');
  }
  clearFeedback('config-user-feedback');
  populateUserCompanySelect();
}

function startUserEdit(userId) {
  const user = cachedUsers.find((item) => item.id === Number(userId));
  if (!user) {
    return;
  }
  editingUserId = user.id;
  const title = document.getElementById('config-user-form-title');
  if (title) {
    title.textContent = 'Editar usuário';
  }
  const cancelButton = document.getElementById('config-user-cancel');
  if (cancelButton) {
    cancelButton.classList.remove('hidden');
  }
  document.getElementById('config-user-name').value = user.full_name;
  document.getElementById('config-user-email').value = user.email;
  document.getElementById('config-user-role').value = user.role;
  populateUserCompanySelect();
  const companySelect = document.getElementById('config-user-company');
  if (companySelect) {
    companySelect.value = user.company_id ? String(user.company_id) : '';
  }
  document.getElementById('config-user-password').value = '';
  document.getElementById('config-user-active').checked = user.is_active !== false;
}

async function refreshUsersSection() {
  if (!isAdminOrStaff()) {
    cachedUsers = [];
    renderUserList([]);
    populateTaskAssigneeSelect();
    updateConfigCounts();
    return;
  }
  const users = await apiRequest('/users');
  cachedUsers = users;
  renderUserList(users);
  populateTaskAssigneeSelect();
  updateConfigCounts();
}

async function handleUserSubmit(event) {
  event.preventDefault();
  if (!isAdminOrStaff()) {
    setFeedback('config-user-feedback', 'Somente o escritório pode gerenciar usuários.', true);
    return;
  }
  const fullName = document.getElementById('config-user-name').value.trim();
  const email = document.getElementById('config-user-email').value.trim().toLowerCase();
  const role = document.getElementById('config-user-role').value;
  const companyValue = document.getElementById('config-user-company').value;
  const password = document.getElementById('config-user-password').value.trim();
  const isActive = document.getElementById('config-user-active').checked;

  if (!fullName || !email) {
    setFeedback('config-user-feedback', 'Informe nome completo e e-mail.', true);
    return;
  }
  if (role === 'client' && !companyValue) {
    setFeedback('config-user-feedback', 'Clientes precisam estar vinculados a uma empresa.', true);
    return;
  }
  if (!editingUserId && password.length < 6) {
    setFeedback('config-user-feedback', 'Defina uma senha com pelo menos 6 caracteres.', true);
    return;
  }

  const payload = {
    full_name: fullName,
    email,
    role,
    company_id: companyValue ? Number(companyValue) : null,
    is_active: isActive
  };
  if (!editingUserId || password) {
    payload.password = password;
  }
  const url = editingUserId ? `/users/${editingUserId}` : '/users';
  const method = editingUserId ? 'PUT' : 'POST';
  try {
    await apiRequest(url, {
      method,
      body: JSON.stringify(payload)
    });
    setFeedback('config-user-feedback', 'Usuário salvo com sucesso!', false);
    await refreshUsersSection();
    resetUserForm();
  } catch (error) {
    setFeedback('config-user-feedback', error.message, true);
  }
}

function handleUserListClick(event) {
  const button = event.target.closest('button[data-action]');
  if (!button) {
    return;
  }
  if (button.dataset.action === 'edit') {
    startUserEdit(button.dataset.id);
  }
}

function renderAccountList(accounts) {
  const list = document.getElementById('config-account-list');
  if (!list) {
    return;
  }
  list.innerHTML = '';
  if (!accounts.length) {
    const empty = document.createElement('li');
    empty.className = 'empty-state';
    empty.textContent = 'Nenhuma conta cadastrada para a empresa selecionada.';
    list.appendChild(empty);
    return;
  }
  accounts.forEach((account) => {
    const li = document.createElement('li');
    const meta = document.createElement('div');
    meta.className = 'item-meta';
    const title = document.createElement('strong');
    title.textContent = account.name;
    meta.appendChild(title);
    const details = document.createElement('span');
    details.className = 'muted small';
    const parts = [];
    if (account.bank_name) {
      parts.push(account.bank_name);
    }
    if (account.account_number) {
      parts.push(`Conta ${account.account_number}`);
    }
    parts.push(`Saldo inicial: ${formatCurrency(account.initial_balance)}`);
    details.textContent = parts.join(' · ');
    meta.appendChild(details);
    li.appendChild(meta);
    list.appendChild(li);
  });
}

async function refreshAccountsSection() {
  const companyId = getActiveCompanyId();
  if (!companyId) {
    cachedAccounts = [];
    renderAccountList([]);
    populateTransactionAccountOptions();
    updateConfigCounts();
    toggleCompanyDependentForms(true);
    return;
  }
  toggleCompanyDependentForms(false);
  const accounts = await apiRequest(`/bank-accounts?company_id=${companyId}`);
  cachedAccounts = accounts;
  renderAccountList(accounts);
  populateTransactionAccountOptions();
  updateConfigCounts();
}

async function handleAccountSubmit(event) {
  event.preventDefault();
  const companyId = getActiveCompanyId();
  if (!companyId) {
    setFeedback('config-account-feedback', 'Selecione uma empresa para cadastrar a conta.', true);
    return;
  }
  const name = document.getElementById('config-account-name').value.trim();
  if (!name) {
    setFeedback('config-account-feedback', 'Informe o nome da conta bancária.', true);
    return;
  }
  const payload = {
    company_id: companyId,
    name,
    bank_name: normalizeStringValue(document.getElementById('config-account-bank').value),
    account_number: normalizeStringValue(document.getElementById('config-account-number').value),
    initial_balance: Number(document.getElementById('config-account-balance').value || 0)
  };
  try {
    await apiRequest('/bank-accounts', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    setFeedback('config-account-feedback', 'Conta cadastrada com sucesso!', false);
    document.getElementById('config-account-form').reset();
    document.getElementById('config-account-balance').value = '0';
    await refreshAccountsSection();
    await refreshTransactionsSection();
    await loadFinancialReport();
  } catch (error) {
    setFeedback('config-account-feedback', error.message, true);
  }
}

function renderCategoryList(categories) {
  const list = document.getElementById('config-category-list');
  if (!list) {
    return;
  }
  list.innerHTML = '';
  if (!categories.length) {
    const empty = document.createElement('li');
    empty.className = 'empty-state';
    empty.textContent = 'Crie categorias para organizar os lançamentos.';
    list.appendChild(empty);
    return;
  }
  categories.forEach((category) => {
    const li = document.createElement('li');
    const meta = document.createElement('div');
    meta.className = 'item-meta';
    const title = document.createElement('strong');
    title.textContent = category.name;
    meta.appendChild(title);
    const info = document.createElement('span');
    info.className = 'muted small';
    info.textContent = category.keywords
      ? `Palavras-chave: ${category.keywords}`
      : 'Sem palavras-chave configuradas';
    meta.appendChild(info);
    li.appendChild(meta);
    list.appendChild(li);
  });
}

async function refreshCategoriesSection() {
  const companyId = getActiveCompanyId();
  if (!companyId) {
    cachedCategories = [];
    renderCategoryList([]);
    populateTransactionCategoryOptions();
    updateConfigCounts();
    return;
  }
  const categories = await apiRequest(`/categories?company_id=${companyId}`);
  cachedCategories = categories;
  renderCategoryList(categories);
  populateTransactionCategoryOptions();
  updateConfigCounts();
}

async function handleCategorySubmit(event) {
  event.preventDefault();
  const companyId = getActiveCompanyId();
  if (!companyId) {
    setFeedback('config-category-feedback', 'Selecione uma empresa para salvar a categoria.', true);
    return;
  }
  const name = document.getElementById('config-category-name').value.trim();
  if (!name) {
    setFeedback('config-category-feedback', 'Informe o nome da categoria.', true);
    return;
  }
  const payload = {
    company_id: companyId,
    name,
    keywords: normalizeStringValue(document.getElementById('config-category-keywords').value),
    color: normalizeStringValue(document.getElementById('config-category-color').value)
  };
  try {
    await apiRequest('/categories', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    setFeedback('config-category-feedback', 'Categoria criada com sucesso!', false);
    document.getElementById('config-category-form').reset();
    document.getElementById('config-category-color').value = '#1f7a8c';
    await refreshCategoriesSection();
    await refreshTransactionsSection();
  } catch (error) {
    setFeedback('config-category-feedback', error.message, true);
  }
}

function renderTransactionList(transactions) {
  const tbody = document.getElementById('config-transaction-list');
  if (!tbody) {
    return;
  }
  tbody.innerHTML = '';
  if (!transactions.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 5;
    cell.className = 'muted';
    cell.textContent = 'Sem lançamentos registrados no período selecionado.';
    row.appendChild(cell);
    tbody.appendChild(row);
    return;
  }
  transactions.slice(0, 20).forEach((transaction) => {
    const row = document.createElement('tr');
    const categoryName = transaction.category_id
      ? cachedCategories.find((category) => category.id === transaction.category_id)?.name
      : null;
    row.innerHTML = `
      <td>${new Date(transaction.date).toLocaleDateString('pt-BR')}</td>
      <td>${transaction.description}</td>
      <td>${transaction.transaction_type === 'inflow' ? 'Entrada' : 'Saída'}</td>
      <td>${formatCurrency(Number(transaction.amount))}</td>
      <td>${categoryName || '-'}</td>
    `;
    tbody.appendChild(row);
  });
}

async function refreshTransactionsSection() {
  const companyId = getActiveCompanyId();
  if (!companyId) {
    cachedTransactions = [];
    renderTransactionList([]);
    return;
  }
  const { start, end } = computePeriodRange('180');
  const transactions = await apiRequest(
    `/transactions?company_id=${companyId}&start_date=${start}&end_date=${end}`
  );
  cachedTransactions = transactions;
  renderTransactionList(transactions);
}

async function handleTransactionSubmit(event) {
  event.preventDefault();
  const companyId = getActiveCompanyId();
  if (!companyId) {
    setFeedback('config-transaction-feedback', 'Selecione uma empresa antes de registrar lançamentos.', true);
    return;
  }
  const description = document.getElementById('config-transaction-description').value.trim();
  const amountValue = Number(document.getElementById('config-transaction-amount').value);
  if (!description || Number.isNaN(amountValue)) {
    setFeedback('config-transaction-feedback', 'Informe a descrição e o valor do lançamento.', true);
    return;
  }
  const payload = {
    company_id: companyId,
    date: document.getElementById('config-transaction-date').value,
    description,
    amount: amountValue,
    transaction_type: document.getElementById('config-transaction-type').value,
    bank_account_id: normalizeStringValue(document.getElementById('config-transaction-account').value),
    category_id: normalizeStringValue(document.getElementById('config-transaction-category').value),
    notes: normalizeStringValue(document.getElementById('config-transaction-notes').value)
  };
  if (!payload.date) {
    setFeedback('config-transaction-feedback', 'Informe a data do lançamento.', true);
    return;
  }
  if (payload.bank_account_id) {
    payload.bank_account_id = Number(payload.bank_account_id);
  }
  if (payload.category_id) {
    payload.category_id = Number(payload.category_id);
  }
  try {
    await apiRequest('/transactions', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    setFeedback('config-transaction-feedback', 'Lançamento registrado!', false);
    const form = document.getElementById('config-transaction-form');
    form.reset();
    document.getElementById('config-transaction-type').value = 'inflow';
    await refreshTransactionsSection();
    await loadFinancialReport();
    await loadHighlights();
  } catch (error) {
    setFeedback('config-transaction-feedback', error.message, true);
  }
}

async function handleImportSubmit(event) {
  event.preventDefault();
  const companyId = getActiveCompanyId();
  if (!companyId) {
    setFeedback('config-import-feedback', 'Selecione uma empresa para importar o extrato.', true);
    return;
  }
  const fileInput = document.getElementById('config-import-file');
  if (!fileInput.files || !fileInput.files.length) {
    setFeedback('config-import-feedback', 'Escolha um arquivo CSV, Excel ou OFX.', true);
    return;
  }
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  try {
    const summary = await apiRequest(`/transactions/import?company_id=${companyId}`, {
      method: 'POST',
      body: formData
    });
    setFeedback(
      'config-import-feedback',
      `Importação concluída: ${summary.imported} lançamentos adicionados.`,
      false
    );
    fileInput.value = '';
    await refreshTransactionsSection();
    await loadFinancialReport();
    await loadHighlights();
  } catch (error) {
    setFeedback('config-import-feedback', error.message, true);
  }
}

function messageFromGoal(item) {
  return item.message || '';
}

function renderGoalProgress(goals) {
  const container = document.getElementById('config-goal-progress');
  if (!container) {
    return;
  }
  container.innerHTML = '';
  if (!goals.length) {
    const empty = document.createElement('p');
    empty.className = 'muted';
    empty.textContent = 'Cadastre metas para acompanhar o avanço das entradas e saídas.';
    container.appendChild(empty);
    return;
  }
  goals.forEach((item) => {
    const card = document.createElement('article');
    card.className = `goal-progress-card status-${item.status}`;
    card.innerHTML = `
      <header>
        <strong>${item.goal.name}</strong>
        <span>${GOAL_DIRECTION_LABELS[item.goal.direction] || item.goal.direction}</span>
      </header>
      <div class="goal-progress-values">
        <span>${formatCurrency(item.actual_amount)}</span>
        <span>de ${formatCurrency(item.goal.target_amount)}</span>
      </div>
      <div class="goal-progress-bar"><div style="width: ${Math.min(item.progress_percentage, 100)}%"></div></div>
      <footer>
        <span class="status-pill status-${item.status}">${GOAL_STATUS_LABELS[item.status] || item.status}</span>
        <span class="muted small">${messageFromGoal(item)}</span>
      </footer>
    `;
    container.appendChild(card);
  });
}

function renderGoalList(goals) {
  const list = document.getElementById('config-goal-list');
  if (!list) {
    return;
  }
  list.innerHTML = '';
  if (!goals.length) {
    const empty = document.createElement('li');
    empty.className = 'empty-state';
    empty.textContent = 'Nenhuma meta cadastrada para a empresa selecionada.';
    list.appendChild(empty);
    return;
  }
  goals.forEach((item) => {
    const { goal, status, progress_percentage } = item;
    const li = document.createElement('li');
    const meta = document.createElement('div');
    meta.className = 'item-meta';

    const title = document.createElement('strong');
    title.textContent = goal.name;
    meta.appendChild(title);

    const period = document.createElement('span');
    period.className = 'muted small';
    period.textContent = `Período: ${formatDate(goal.period_start)} até ${formatDate(goal.period_end)}`;
    meta.appendChild(period);

    const details = document.createElement('span');
    details.className = 'muted small';
    details.textContent = `${GOAL_DIRECTION_LABELS[goal.direction] || goal.direction} · ${progress_percentage.toFixed(0)}%`;
    meta.appendChild(details);

    if (goal.archived) {
      const archived = document.createElement('span');
      archived.className = 'status-pill status-archived';
      archived.textContent = 'Arquivada';
      meta.appendChild(archived);
    } else {
      const statusPill = document.createElement('span');
      statusPill.className = `status-pill status-${status}`;
      statusPill.textContent = GOAL_STATUS_LABELS[status] || status;
      meta.appendChild(statusPill);
    }

    li.appendChild(meta);

    const actions = document.createElement('div');
    actions.className = 'item-actions';
    const editButton = document.createElement('button');
    editButton.className = 'inline';
    editButton.dataset.action = 'edit';
    editButton.dataset.id = goal.id;
    editButton.textContent = 'Editar';
    actions.appendChild(editButton);

    const deleteButton = document.createElement('button');
    deleteButton.className = 'inline';
    deleteButton.dataset.action = 'delete';
    deleteButton.dataset.id = goal.id;
    deleteButton.textContent = 'Remover';
    actions.appendChild(deleteButton);

    li.appendChild(actions);
    list.appendChild(li);
  });
}

function resetGoalForm() {
  const form = document.getElementById('config-goal-form');
  if (!form) {
    return;
  }
  form.reset();
  editingGoalId = null;
  const title = document.getElementById('config-goal-form-title');
  if (title) {
    title.textContent = 'Nova meta';
  }
  document.getElementById('config-goal-direction').value = 'inflow';
  document.getElementById('config-goal-archived').checked = false;
  const cancelButton = document.getElementById('config-goal-cancel');
  if (cancelButton) {
    cancelButton.classList.add('hidden');
  }
  clearFeedback('config-goal-feedback');
}

function startGoalEdit(goalId) {
  const goal = cachedGoals.find((item) => item.goal.id === Number(goalId));
  if (!goal) {
    return;
  }
  editingGoalId = goal.goal.id;
  const title = document.getElementById('config-goal-form-title');
  if (title) {
    title.textContent = 'Editar meta';
  }
  const cancelButton = document.getElementById('config-goal-cancel');
  if (cancelButton) {
    cancelButton.classList.remove('hidden');
  }
  document.getElementById('config-goal-name').value = goal.goal.name;
  document.getElementById('config-goal-description').value = goal.goal.description || '';
  document.getElementById('config-goal-direction').value = goal.goal.direction;
  document.getElementById('config-goal-target').value = goal.goal.target_amount;
  document.getElementById('config-goal-start').value = goal.goal.period_start;
  document.getElementById('config-goal-end').value = goal.goal.period_end;
  document.getElementById('config-goal-archived').checked = Boolean(goal.goal.archived);
}

async function refreshGoalsSection() {
  const companyId = getActiveCompanyId();
  if (!companyId) {
    cachedGoals = [];
    renderGoalList([]);
    renderGoalProgress([]);
    updateConfigCounts();
    return;
  }
  try {
    const goals = await apiRequest(`/financial-goals?company_id=${companyId}`);
    cachedGoals = goals;
    renderGoalList(goals);
    renderGoalProgress(goals);
    updateConfigCounts();
  } catch (error) {
    setFeedback('config-goal-feedback', error.message, true);
  }
}

async function handleGoalSubmit(event) {
  event.preventDefault();
  const companyId = getActiveCompanyId();
  if (!companyId && !editingGoalId) {
    setFeedback('config-goal-feedback', 'Escolha a empresa antes de salvar a meta.', true);
    return;
  }
  const targetInput = document.getElementById('config-goal-target');
  const targetAmount = Number(targetInput.value);
  if (!Number.isFinite(targetAmount) || targetAmount <= 0) {
    setFeedback('config-goal-feedback', 'Informe um valor de meta maior que zero.', true);
    return;
  }
  const startValue = document.getElementById('config-goal-start').value;
  const endValue = document.getElementById('config-goal-end').value;
  if (startValue && endValue && new Date(endValue) < new Date(startValue)) {
    setFeedback('config-goal-feedback', 'A data final deve ser posterior ou igual ao início da meta.', true);
    return;
  }

  const payload = {
    name: document.getElementById('config-goal-name').value.trim(),
    description: normalizeStringValue(document.getElementById('config-goal-description').value),
    direction: document.getElementById('config-goal-direction').value,
    target_amount: targetAmount,
    period_start: startValue,
    period_end: endValue,
    archived: document.getElementById('config-goal-archived').checked
  };

  const isEditing = Boolean(editingGoalId);
  const url = isEditing ? `/financial-goals/${editingGoalId}` : '/financial-goals';
  const method = isEditing ? 'PUT' : 'POST';
  if (!isEditing) {
    payload.company_id = companyId;
  }
  try {
    await apiRequest(url, {
      method,
      body: JSON.stringify(payload)
    });
    setFeedback('config-goal-feedback', 'Meta salva com sucesso!', false);
    await refreshGoalsSection();
    await loadGoalSummary();
    resetGoalForm();
  } catch (error) {
    setFeedback('config-goal-feedback', error.message, true);
  }
}

async function handleGoalListClick(event) {
  const button = event.target.closest('button[data-action]');
  if (!button) {
    return;
  }
  const goalId = button.dataset.id;
  if (button.dataset.action === 'edit') {
    startGoalEdit(goalId);
    return;
  }
  if (button.dataset.action === 'delete') {
    const confirmed = window.confirm('Deseja remover esta meta?');
    if (!confirmed) {
      return;
    }
    try {
      await apiRequest(`/financial-goals/${goalId}`, { method: 'DELETE' });
      await refreshGoalsSection();
      await loadGoalSummary();
      setFeedback('config-goal-feedback', 'Meta removida.', false);
    } catch (error) {
      setFeedback('config-goal-feedback', error.message, true);
    }
  }
}

function renderTaskList(tasks) {
  const list = document.getElementById('config-task-list');
  if (!list) {
    return;
  }
  list.innerHTML = '';
  if (!tasks.length) {
    const empty = document.createElement('li');
    empty.className = 'empty-state';
    empty.textContent = 'Nenhuma tarefa cadastrada para a empresa selecionada.';
    list.appendChild(empty);
    return;
  }
  tasks.forEach((task) => {
    const li = document.createElement('li');
    const meta = document.createElement('div');
    meta.className = 'item-meta';
    const title = document.createElement('strong');
    title.textContent = task.title;
    meta.appendChild(title);
    if (task.description) {
      const description = document.createElement('span');
      description.className = 'muted';
      description.textContent = task.description;
      meta.appendChild(description);
    }
    const info = document.createElement('span');
    info.className = 'muted small';
    const due = task.due_date ? `Até ${formatDate(task.due_date)}` : 'Sem prazo definido';
    const owner = task.assigned_to ? task.assigned_to.full_name : 'Sem responsável';
    info.textContent = `${TASK_STATUS_LABELS[task.status] || task.status} · ${due} · ${owner}`;
    meta.appendChild(info);
    li.appendChild(meta);

    const actions = document.createElement('div');
    actions.className = 'item-actions';
    const editButton = document.createElement('button');
    editButton.className = 'inline';
    editButton.dataset.action = 'edit';
    editButton.dataset.id = task.id;
    editButton.textContent = 'Editar';
    actions.appendChild(editButton);

    if (task.status !== 'done') {
      const completeButton = document.createElement('button');
      completeButton.className = 'inline';
      completeButton.dataset.action = 'complete';
      completeButton.dataset.id = task.id;
      completeButton.textContent = 'Concluir';
      actions.appendChild(completeButton);
    }

    const deleteButton = document.createElement('button');
    deleteButton.className = 'inline';
    deleteButton.dataset.action = 'delete';
    deleteButton.dataset.id = task.id;
    deleteButton.textContent = 'Remover';
    actions.appendChild(deleteButton);

    li.appendChild(actions);
    list.appendChild(li);
  });
}

function resetTaskForm() {
  const form = document.getElementById('config-task-form');
  if (!form) {
    return;
  }
  form.reset();
  editingTaskId = null;
  const title = document.getElementById('config-task-form-title');
  if (title) {
    title.textContent = 'Nova tarefa';
  }
  const cancelButton = document.getElementById('config-task-cancel');
  if (cancelButton) {
    cancelButton.classList.add('hidden');
  }
  document.getElementById('config-task-status').value = 'open';
  populateTaskAssigneeSelect();
  clearFeedback('config-task-feedback');
}

function startTaskEdit(taskId) {
  const task = cachedTasks.find((item) => item.id === Number(taskId));
  if (!task) {
    return;
  }
  editingTaskId = task.id;
  const title = document.getElementById('config-task-form-title');
  if (title) {
    title.textContent = 'Editar tarefa';
  }
  const cancelButton = document.getElementById('config-task-cancel');
  if (cancelButton) {
    cancelButton.classList.remove('hidden');
  }
  document.getElementById('config-task-title').value = task.title;
  document.getElementById('config-task-description').value = task.description || '';
  document.getElementById('config-task-status').value = task.status;
  document.getElementById('config-task-due').value = task.due_date || '';
  populateTaskAssigneeSelect();
  const ownerSelect = document.getElementById('config-task-owner');
  if (ownerSelect) {
    ownerSelect.value = task.assigned_to ? String(task.assigned_to.id) : '';
  }
}

async function refreshTasksSection() {
  const companyId = getActiveCompanyId();
  if (!companyId) {
    cachedTasks = [];
    renderTaskList([]);
    updateConfigCounts();
    return;
  }
  try {
    const tasks = await apiRequest(`/tasks?company_id=${companyId}`);
    cachedTasks = tasks;
    renderTaskList(tasks);
    populateTaskAssigneeSelect();
    updateConfigCounts();
  } catch (error) {
    setFeedback('config-task-feedback', error.message, true);
  }
}

async function handleTaskSubmit(event) {
  event.preventDefault();
  const companyId = getActiveCompanyId();
  if (!companyId && !editingTaskId) {
    setFeedback('config-task-feedback', 'Escolha a empresa antes de salvar a tarefa.', true);
    return;
  }
  const payload = {
    title: document.getElementById('config-task-title').value.trim(),
    description: normalizeStringValue(document.getElementById('config-task-description').value),
    due_date: normalizeStringValue(document.getElementById('config-task-due').value),
    status: document.getElementById('config-task-status').value,
    assigned_to_id: normalizeStringValue(document.getElementById('config-task-owner').value)
  };

  if (!payload.title) {
    setFeedback('config-task-feedback', 'Informe um título para a tarefa.', true);
    return;
  }

  if (payload.assigned_to_id) {
    payload.assigned_to_id = Number(payload.assigned_to_id);
  } else {
    payload.assigned_to_id = null;
  }

  const isEditing = Boolean(editingTaskId);
  const url = isEditing ? `/tasks/${editingTaskId}` : '/tasks';
  const method = isEditing ? 'PUT' : 'POST';
  if (!isEditing) {
    payload.company_id = companyId;
  }
  try {
    await apiRequest(url, {
      method,
      body: JSON.stringify(payload)
    });
    setFeedback('config-task-feedback', 'Tarefa salva com sucesso!', false);
    await refreshTasksSection();
    await loadTaskSummary();
    resetTaskForm();
  } catch (error) {
    setFeedback('config-task-feedback', error.message, true);
  }
}

async function handleTaskListClick(event) {
  const button = event.target.closest('button[data-action]');
  if (!button) {
    return;
  }
  const taskId = button.dataset.id;
  if (button.dataset.action === 'edit') {
    startTaskEdit(taskId);
    return;
  }
  if (button.dataset.action === 'complete') {
    try {
      await apiRequest(`/tasks/${taskId}`, {
        method: 'PUT',
        body: JSON.stringify({ status: 'done' })
      });
      await refreshTasksSection();
      await loadTaskSummary();
    } catch (error) {
      setFeedback('config-task-feedback', error.message, true);
    }
    return;
  }
  if (button.dataset.action === 'delete') {
    const confirmed = window.confirm('Deseja remover esta tarefa?');
    if (!confirmed) {
      return;
    }
    try {
      await apiRequest(`/tasks/${taskId}`, { method: 'DELETE' });
      await refreshTasksSection();
      await loadTaskSummary();
      setFeedback('config-task-feedback', 'Tarefa removida.', false);
    } catch (error) {
      setFeedback('config-task-feedback', error.message, true);
    }
  }
}

async function showConfigTab(tab) {
  currentConfigTab = tab;
  const menuButtons = document.querySelectorAll('#config-menu button[data-tab]');
  menuButtons.forEach((button) => {
    button.classList.toggle('active', button.dataset.tab === tab);
  });
  const panels = document.querySelectorAll('.config-panel');
  panels.forEach((panel) => {
    const isActive = panel.dataset.panel === tab;
    panel.classList.toggle('active', isActive);
  });

  if (tab === 'overview') {
    await refreshCompaniesSection();
    if (isAdminOrStaff()) {
      await refreshUsersSection();
    } else {
      cachedUsers = [];
      renderUserList([]);
    }
    await refreshAccountsSection();
    await refreshCategoriesSection();
    await refreshTransactionsSection();
    await refreshGoalsSection();
    await refreshTasksSection();
    updateConfigCounts();
  } else if (tab === 'companies') {
    await refreshCompaniesSection();
  } else if (tab === 'users') {
    await refreshUsersSection();
  } else if (tab === 'accounts') {
    await refreshAccountsSection();
  } else if (tab === 'categories') {
    await refreshCategoriesSection();
  } else if (tab === 'transactions') {
    await refreshAccountsSection();
    await refreshCategoriesSection();
    await refreshTransactionsSection();
  } else if (tab === 'imports') {
    await refreshAccountsSection();
    await refreshCategoriesSection();
  } else if (tab === 'goals') {
    await refreshGoalsSection();
  } else if (tab === 'tasks') {
    await refreshUsersSection();
    await refreshTasksSection();
  }
}

async function openConfigLayer() {
  if (!currentUser) {
    return;
  }
  const layer = document.getElementById('config-layer');
  if (!layer) {
    return;
  }
  layer.classList.remove('hidden');
  layer.setAttribute('aria-hidden', 'false');
  const initialTab = currentConfigTab === 'users' && !isAdminOrStaff() ? 'overview' : currentConfigTab;
  try {
    await showConfigTab(initialTab);
  } catch (error) {
    console.error('Falha ao carregar configurações:', error);
    setFeedback('config-company-feedback', 'Não foi possível carregar as configurações.', true);
  }
  document.addEventListener('keydown', handleEscapeKey);
}

function closeConfigLayer() {
  const layer = document.getElementById('config-layer');
  if (!layer) {
    return;
  }
  layer.classList.add('hidden');
  layer.setAttribute('aria-hidden', 'true');
  document.removeEventListener('keydown', handleEscapeKey);
}

async function handleConfigTabClick(event) {
  const button = event.target.closest('button[data-tab]');
  if (!button || button.classList.contains('hidden')) {
    return;
  }
  const tab = button.dataset.tab;
  try {
    await showConfigTab(tab);
  } catch (error) {
    console.error('Erro ao trocar de aba de configuração:', error);
  }
}

async function handleConfigCompanyChange(event) {
  const value = event.target.value;
  configCompanyId = value ? Number(value) : null;
  populateUserCompanySelect();
  try {
    await refreshAccountsSection();
    await refreshCategoriesSection();
    await refreshTransactionsSection();
    await refreshGoalsSection();
    await refreshTasksSection();
    await loadGoalSummary();
    await loadTaskSummary();
  } catch (error) {
    console.error('Erro ao atualizar dados da empresa selecionada:', error);
  }
}

function handleEscapeKey(event) {
  if (event.key === 'Escape') {
    const layer = document.getElementById('config-layer');
    if (layer && !layer.classList.contains('hidden')) {
      closeConfigLayer();
    }
  }
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
    cachedCompanies = [];
    cachedUsers = [];
    cachedAccounts = [];
    cachedCategories = [];
    cachedTransactions = [];
    cachedGoals = [];
    cachedTasks = [];
    configCompanyId = currentUser.role === 'client' ? currentUser.company_id || null : null;
    currentConfigTab = 'overview';
    editingCompanyId = null;
    editingUserId = null;
    editingGoalId = null;
    editingTaskId = null;
    resetCompanyForm();
    resetUserForm();
    const accountForm = document.getElementById('config-account-form');
    if (accountForm) {
      accountForm.reset();
      const balanceField = document.getElementById('config-account-balance');
      if (balanceField) {
        balanceField.value = '0';
      }
    }
    const categoryForm = document.getElementById('config-category-form');
    if (categoryForm) {
      categoryForm.reset();
      const colorField = document.getElementById('config-category-color');
      if (colorField) {
        colorField.value = '#1f7a8c';
      }
    }
    const transactionForm = document.getElementById('config-transaction-form');
    if (transactionForm) {
      transactionForm.reset();
      const typeField = document.getElementById('config-transaction-type');
      if (typeField) {
        typeField.value = 'inflow';
      }
    }
    const importForm = document.getElementById('config-import-form');
    if (importForm) {
      importForm.reset();
    }
    resetGoalForm();
    resetTaskForm();
    clearFeedback('config-account-feedback');
    clearFeedback('config-category-feedback');
    clearFeedback('config-transaction-feedback');
    clearFeedback('config-import-feedback');
    clearFeedback('config-goal-feedback');
    clearFeedback('config-task-feedback');
    updateRoleBasedUI();
    populateTaskAssigneeSelect();
    document.getElementById('welcome').textContent = `Olá, ${currentUser.full_name}!`;
    toggleView(true);
    await populateCompanies();
    updatePeriodButtons(periodPreset);
    await loadHighlights();
    await loadFinancialReport();
    await loadGoalSummary();
    await loadTaskSummary();
  } catch (error) {
    errorElement.textContent = error.message;
  }
}

function handleLogout() {
  token = null;
  currentUser = null;
  selectedCompany = null;
  periodPreset = '90';
  cachedCompanies = [];
  cachedUsers = [];
  cachedAccounts = [];
  cachedCategories = [];
  cachedTransactions = [];
  cachedGoals = [];
  cachedTasks = [];
  configCompanyId = null;
  currentConfigTab = 'overview';
  editingCompanyId = null;
  editingUserId = null;
  editingGoalId = null;
  editingTaskId = null;
  if (cashflowChart) {
    cashflowChart.destroy();
    cashflowChart = null;
  }
  closeConfigLayer();
  resetCompanyForm();
  resetUserForm();
  const accountForm = document.getElementById('config-account-form');
  if (accountForm) {
    accountForm.reset();
    const balanceField = document.getElementById('config-account-balance');
    if (balanceField) {
      balanceField.value = '0';
    }
  }
  const categoryForm = document.getElementById('config-category-form');
  if (categoryForm) {
    categoryForm.reset();
    const colorField = document.getElementById('config-category-color');
    if (colorField) {
      colorField.value = '#1f7a8c';
    }
  }
  const transactionForm = document.getElementById('config-transaction-form');
  if (transactionForm) {
    transactionForm.reset();
    const typeField = document.getElementById('config-transaction-type');
    if (typeField) {
      typeField.value = 'inflow';
    }
  }
  const importForm = document.getElementById('config-import-form');
  if (importForm) {
    importForm.reset();
  }
  resetGoalForm();
  resetTaskForm();
  clearFeedback('config-company-feedback');
  clearFeedback('config-user-feedback');
  clearFeedback('config-account-feedback');
  clearFeedback('config-category-feedback');
  clearFeedback('config-transaction-feedback');
  clearFeedback('config-import-feedback');
  clearFeedback('config-goal-feedback');
  clearFeedback('config-task-feedback');
  updateRoleBasedUI();
  updateConfigCounts();
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
    loadGoalSummary();
    loadTaskSummary();
  });
  document.getElementById('open-config').addEventListener('click', (event) => {
    event.preventDefault();
    openConfigLayer();
  });
  document.getElementById('close-config').addEventListener('click', (event) => {
    event.preventDefault();
    closeConfigLayer();
  });
  document.getElementById('config-menu').addEventListener('click', handleConfigTabClick);
  document.getElementById('config-company-form').addEventListener('submit', handleCompanySubmit);
  document.getElementById('config-company-cancel').addEventListener('click', resetCompanyForm);
  document.getElementById('config-company-list').addEventListener('click', handleCompanyListClick);
  document.getElementById('config-user-form').addEventListener('submit', handleUserSubmit);
  document.getElementById('config-user-cancel').addEventListener('click', resetUserForm);
  document.getElementById('config-user-list').addEventListener('click', handleUserListClick);
  document.getElementById('config-account-form').addEventListener('submit', handleAccountSubmit);
  document.getElementById('config-category-form').addEventListener('submit', handleCategorySubmit);
  document.getElementById('config-transaction-form').addEventListener('submit', handleTransactionSubmit);
  document.getElementById('config-import-form').addEventListener('submit', handleImportSubmit);
  document.getElementById('config-goal-form').addEventListener('submit', handleGoalSubmit);
  document.getElementById('config-goal-cancel').addEventListener('click', resetGoalForm);
  document.getElementById('config-goal-list').addEventListener('click', handleGoalListClick);
  document.getElementById('config-task-form').addEventListener('submit', handleTaskSubmit);
  document.getElementById('config-task-cancel').addEventListener('click', resetTaskForm);
  document.getElementById('config-task-list').addEventListener('click', handleTaskListClick);
  document.getElementById('config-company-focus').addEventListener('change', handleConfigCompanyChange);
}

window.addEventListener('DOMContentLoaded', () => {
  registerEventListeners();
  updatePeriodButtons(periodPreset);
});
