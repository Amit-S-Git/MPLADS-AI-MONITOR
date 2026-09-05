(() => {
  const $ = id => document.getElementById(id);
  let allProjects = [];
  let visibleProjects = [];

  const isPublicMode = () => sessionStorage.getItem('mpladsLoggedIn') !== 'true';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const money = value => `₹${Number(value || 0).toFixed(2)} Lakh`;
  const unique = values => [...new Set(values.filter(Boolean))].sort((a,b) => a.localeCompare(b));

  function setSelect(id, values, allLabel) {
    const select = $(id); if (!select) return;
    const current = select.value;
    select.innerHTML = `<option value="">${allLabel}</option>` + values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
    if (values.includes(current)) select.value = current;
  }

  function rebuildDependentFilters() {
    const state = $('publicStateFilter').value;
    const district = $('publicDistrictFilter').value;
    const stateRows = state ? allProjects.filter(p => p.state === state) : allProjects;
    setSelect('publicDistrictFilter', unique(stateRows.map(p => p.district)), 'All Districts');
    if (district && stateRows.some(p => p.district === district)) $('publicDistrictFilter').value = district;
    const selectedDistrict = $('publicDistrictFilter').value;
    const districtRows = selectedDistrict ? stateRows.filter(p => p.district === selectedDistrict) : stateRows;
    setSelect('publicConstituencyFilter', unique(districtRows.map(p => p.constituency)), 'All Constituencies');
  }

  function populateFilters() {
    setSelect('publicStateFilter', unique(allProjects.map(p => p.state)), 'All States');
    setSelect('publicDistrictFilter', unique(allProjects.map(p => p.district)), 'All Districts');
    setSelect('publicConstituencyFilter', unique(allProjects.map(p => p.constituency)), 'All Constituencies');
  }

  function getFilters() {
    return {
      state: $('publicStateFilter').value,
      district: $('publicDistrictFilter').value,
      constituency: $('publicConstituencyFilter').value,
      status: $('publicStatusFilter').value,
      project: $('publicProjectSearch').value.trim().toLowerCase(),
      quick: $('publicQuickSearch').value.trim().toLowerCase()
    };
  }

  function matches(p, f) {
    if (f.state && p.state !== f.state) return false;
    if (f.district && p.district !== f.district) return false;
    if (f.constituency && p.constituency !== f.constituency) return false;
    if (f.status && p.status !== f.status) return false;
    const projectText = `${p.id} ${p.name}`.toLowerCase();
    if (f.project && !projectText.includes(f.project)) return false;
    const allText = `${p.id} ${p.name} ${p.state} ${p.district} ${p.constituency} ${p.status}`.toLowerCase();
    if (f.quick && !allText.includes(f.quick)) return false;
    return true;
  }

  function renderSummary() {
    const total = visibleProjects.length;
    $('publicTotalWorks').textContent = total;
    $('publicOngoingWorks').textContent = visibleProjects.filter(p => p.status === 'Ongoing').length;
    $('publicCompletedWorks').textContent = visibleProjects.filter(p => p.status === 'Completed').length;
    $('publicSanctionedAmount').textContent = money(visibleProjects.reduce((s,p) => s + Number(p.sanctioned || 0), 0));
    $('publicSpentAmount').textContent = money(visibleProjects.reduce((s,p) => s + Number(p.spent || 0), 0));
    $('publicResultText').textContent = `Showing ${total} work${total === 1 ? '' : 's'}`;
  }

  function renderTable() {
    const body = $('publicWorksBody');
    const empty = $('publicEmptyMessage');
    if (!visibleProjects.length) {
      body.innerHTML = ''; empty.hidden = false; return;
    }
    empty.hidden = true;
    body.innerHTML = visibleProjects.map((p, i) => `
      <tr>
        <td>${i + 1}</td><td><strong>${esc(p.id)}</strong></td><td>${esc(p.state)}</td><td>${esc(p.district)}</td>
        <td>${esc(p.constituency)}</td><td class="public-project-name">${esc(p.name)}</td><td>${money(p.sanctioned)}</td>
        <td>${Math.round(Number(p.progress || 0))}%</td><td><span class="public-status ${esc(String(p.status).toLowerCase())}">${esc(p.status)}</span></td>
      </tr>`).join('');
  }

  function applyFilters() {
    visibleProjects = allProjects.filter(p => matches(p, getFilters()));
    renderSummary(); renderTable();
  }

  function resetFilters() {
    $('publicFilterForm').reset(); $('publicQuickSearch').value = '';
    populateFilters(); applyFilters();
  }

  async function loadProjects() {
    try {
      const response = await fetch('/api/public-projects', {headers:{Accept:'application/json'}});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      allProjects = await response.json();
      if (!Array.isArray(allProjects)) allProjects = [];
      populateFilters(); visibleProjects = [...allProjects]; renderSummary(); renderTable();
    } catch (error) {
      console.error('Public dashboard data error:', error);
      $('publicWorksBody').innerHTML = '';
      $('publicEmptyMessage').hidden = false;
      $('publicEmptyMessage').textContent = 'Project data could not be loaded. Start the website using app.py, not Live Server.';
    }
  }

  function init() {
    if (!isPublicMode() || !$('publicDashboardView')) return;
    $('publicLastUpdated').textContent = new Date().toLocaleString('en-IN', {dateStyle:'medium', timeStyle:'short'});
    $('publicFilterForm').addEventListener('submit', e => { e.preventDefault(); applyFilters(); });
    $('publicResetButton').addEventListener('click', resetFilters);
    $('publicQuickSearch').addEventListener('input', applyFilters);
    $('publicStateFilter').addEventListener('change', () => { rebuildDependentFilters(); });
    $('publicDistrictFilter').addEventListener('change', () => { rebuildDependentFilters(); });
    loadProjects();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
