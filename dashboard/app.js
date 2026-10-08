const accents = ["#2bd9c5", "#75a9ff", "#ffbe55", "#ff6d75"];
const fmt = new Intl.NumberFormat("en-US");
let dashboard;

const pct = (value, digits = 1) => `${(Number(value) * 100).toFixed(digits)}%`;
const label = value => ({ balanced_reference: "Balanced", customer_first: "Customer first", loss_first: "Loss first" }[value] || value);

function selectedPolicy() {
  const scenario = document.querySelector("#scenario").value;
  const capacity = Number(document.querySelector("#capacity").value);
  const policy = dashboard.policy.find(row => row.scenario === scenario && row.partition === "oot" && row.review_capacity === capacity);
  const actions = dashboard.actions.filter(row => row.scenario === scenario && row.partition === "oot" && row.review_capacity === capacity);
  return { scenario, policy, actions };
}

function renderPolicy() {
  const { scenario, policy, actions } = selectedPolicy();
  document.querySelector("#prevented").textContent = pct(policy.prevented_exposure_proxy_rate);
  document.querySelector("#utilisation").textContent = pct(policy.review_capacity_utilisation);
  document.querySelector("#reviews").textContent = `${policy.mean_daily_reviews.toFixed(1)} mean reviews / day`;
  document.querySelector("#costReduction").textContent = `${fmt.format(Math.round(policy.proxy_cost_reduction))} scenario units`;
  document.querySelector("#policySummary").textContent = `${label(scenario)} policy intervenes on ${pct(policy.intervention_rate)} of transactions and reaches ${pct(policy.fraud_case_intervention_rate)} of fraud cases.`;
  document.querySelector("#actionFlow").innerHTML = actions.map((action, index) => `
    <article class="action" style="--accent:${accents[index]}">
      <span class="action-name">${action.action.replace("_", " ")}</span>
      <strong>${fmt.format(action.transactions)}</strong>
      <small>transactions routed</small>
      <div class="risk">Observed fraud rate · <b>${pct(action.fraud_rate, 2)}</b></div>
    </article>`).join("");
}

function renderModels() {
  const baseline = dashboard.baseline_models.find(row => row.model === "linear" && row.partition === "oot");
  const selectedName = dashboard.challenger_decision.selected_on_policy_window;
  const challenger = dashboard.challenger_models.find(row => row.model === selectedName && row.partition === "oot");
  const models = [["Linear reference", baseline.average_precision], ["Governed transaction GBM", challenger.average_precision]];
  document.querySelector("#modelBars").innerHTML = models.map(([name, value]) => `
    <div class="bar-row"><span class="bar-label">${name}</span><div class="bar-track"><div class="bar-fill" style="width:${value / .5 * 100}%"></div></div><span class="bar-value">${value.toFixed(3)}</span></div>`).join("");

  const order = ["gbm_transaction", "gbm_plus_identity", "gbm_plus_behaviour"];
  const names = { gbm_transaction: "Transaction core", gbm_plus_identity: "+ identity", gbm_plus_behaviour: "+ behaviour" };
  document.querySelector("#ablationTable").innerHTML = `
    <div class="table-row header"><span>Feature family</span><span>Precision@100</span><span>AP</span><span>Brier ↓</span></div>` +
    order.map(name => {
      const row = dashboard.ablation.find(item => item.model === name);
      return `<div class="table-row"><span>${names[name]}</span><span>${pct(row.mean_precision_at_k)}</span><span>${row.average_precision.toFixed(3)}</span><span>${row.brier_score.toFixed(4)}</span></div>`;
    }).join("");
}

function linePath(values, width, height, max) {
  return values.map((value, index) => `${index ? "L" : "M"}${(index / (values.length - 1) * width).toFixed(1)},${(height - value / max * height).toFixed(1)}`).join(" ");
}

function renderMonitoring() {
  const values = dashboard.monitoring;
  const width = 640, height = 210, max = .1;
  const psi = values.map(row => row.score_psi);
  const ece = values.map(row => row.ece);
  document.querySelector("#monitorChart").innerHTML = `<svg viewBox="0 0 ${width + 70} ${height + 40}" role="img">
    <title>Score PSI and calibration error across six holdout weeks</title>
    ${[0,.025,.05,.075,.1].map(value => `<line class="gridline" x1="35" y1="${height - value/max*height}" x2="${width+35}" y2="${height - value/max*height}"/><text class="chart-label" x="0" y="${height - value/max*height + 4}">${value.toFixed(3)}</text>`).join("")}
    <path class="psi-line" d="${linePath(psi,width,height,max)}" transform="translate(35 0)"/><path class="ece-line" d="${linePath(ece,width,height,max)}" transform="translate(35 0)"/>
    ${values.map((row,index) => `<text class="chart-label" x="${35 + index/(values.length-1)*width}" y="${height+25}" text-anchor="middle">W${row.elapsed_week}</text>`).join("")}
    <line x1="35" x2="${width+35}" y1="0" y2="0" stroke="#ffbe55" stroke-dasharray="5 5" opacity=".45"/><text class="chart-label" x="${width+35}" y="-7" text-anchor="end">amber PSI 0.10</text>
  </svg>`;
  document.querySelector("#delayCards").innerHTML = dashboard.delayed_labels.map(row => `
    <div class="delay-card"><span>${row.delay_days}-day label delay</span><strong>${pct(row.mean_label_coverage)}</strong><small>mean labels available · Brier Δ ${row.brier_change.toFixed(6)}</small></div>`).join("");
}

function renderTimeline() {
  const colours = { development: "#75a9ff", calibration: "#2bd9c5", policy: "#ffbe55", oot: "#ff6d75" };
  const descriptions = { development: "Fit models", calibration: "Calibrate scores", policy: "Choose policy", oot: "Locked final test" };
  const ordered = ["development", "calibration", "policy", "oot"].map(name => dashboard.partitions.find(row => row.partition === name));
  document.querySelector("#timeline").innerHTML = ordered.map(row => `
    <div class="period" style="--accent:${colours[row.partition]}"><span>${row.partition}</span><small>${fmt.format(row.rows)} rows</small><small>${descriptions[row.partition]}</small></div>`).join("");
}

async function init() {
  dashboard = await fetch("data.json").then(response => response.json());
  renderPolicy();
  renderModels();
  renderMonitoring();
  renderTimeline();
  document.querySelector("#scenario").addEventListener("change", renderPolicy);
  document.querySelector("#capacity").addEventListener("change", renderPolicy);
}

init().catch(error => {
  document.querySelector("#actionFlow").innerHTML = `<p class="note">Dashboard data could not load: ${error.message}</p>`;
});
