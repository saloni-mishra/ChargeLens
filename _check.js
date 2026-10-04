
    let currentData = [];

    // Currency Formatter
    function fmtMoney(amount, currency) {
      if (amount === null || amount === undefined) return 'N/A';

      const symbols = {
        INR: '₹',
        USD: '$',
        EUR: '€',
        GBP: '£',
        CAD: 'C$',
        AUD: 'A$'
      };

      const sym = symbols[currency] || (currency ? currency + ' ' : '');

      return `${sym}${Number(amount).toLocaleString()}`;
    }

    // XSS Sanitizer
    function sanitize(str) {
      if (str === null || str === undefined) return '';

      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    async function loadBudget() {
      try {
        const res = await fetch('/api/budget');
        const data = await res.json();

        document.getElementById('budgetMeter').innerText =
          `SerpApi Used: ${data.used} / ${data.total} | Reserve: ${data.demo_reserve}`;

      } catch (e) {
        document.getElementById('budgetMeter').innerText = 'Local Offline Mode';
      }
    }

    loadBudget();

    function renderLoadingStage() {
      document.getElementById('metricsBar').style.display = 'none';
      document.getElementById('decisionPanel').style.display = 'none';

      document.getElementById('resultsGrid').innerHTML = `
        <div class="loading-container" style="grid-column: 1 / -1;">

          <h3 style="margin: 0 0 16px;">Analyzing Statement</h3>

          <div class="loading-step done">
            ✓ 1. Parsing statement & cleaning transaction prefixes locally
          </div>

          <div class="loading-step done">
            ✓ 2. Evaluating recurring timing & charge patterns
          </div>

          <div class="loading-step active">
            <span class="spinner"></span>
            3. Resolving canonical services & checking pricing cache
          </div>

          <div class="loading-step">
            <span class="spinner"></span>
            4. Running deterministic validation rules
          </div>

          <p style="font-size: 12px; color: var(--text-muted); margin-top: 20px; border-top: 1px solid var(--border); padding-top: 12px;">
            Enforcing budget guard policy: external search is skipped for unresolved services.
          </p>

        </div>
      `;
    }

    async function uploadStatement(e) {
      const file = e.target.files[0];

      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);

      renderLoadingStage();

      try {
        const res = await fetch("/api/analyze", {
          method: "POST",
          body: formData
        });

        if (!res.ok) {
          throw new Error(`Server returned HTTP ${res.status}`);
        }

        const data = await res.json();

        currentData = data.results || [];

        renderMetrics(currentData);
        renderCards(currentData);
        loadBudget();

      } catch (err) {

        document.getElementById('metricsBar').style.display = 'none';
        document.getElementById('decisionPanel').style.display = 'none';

        document.getElementById('resultsGrid').innerHTML = `
          <div class="card" style="grid-column: 1 / -1; border-color: var(--yellow);">

            <div class="merchant">Analysis Failed</div>

            <div class="detail" style="margin-top: 8px;">
              ${sanitize(err.message)}.
              Please check your CSV/PDF format
              (CSV requires columns: <code>date, amount, currency, raw_description</code>; PDF must contain a readable statement table or text)
              and verify your API keys.
            </div>

          </div>
        `;
      }
    }

    function renderMetrics(items) {

      const bar = document.getElementById('metricsBar');

      if (!items || items.length === 0) {
        bar.style.display = 'none';
        document.getElementById('decisionPanel').style.display = 'none';
        return;
      }

      const totalMonthlySpend = items.reduce(
        (acc, it) => acc + (it.user_amount || 0),
        0
      );

      const highConfidenceItems = items.filter(
  it => it.confidence_tier === 'HIGH'
);

      const verifiedCount = highConfidenceItems.length;

      // STRICT RULE:
      // Only count verified HIGH confidence differences
      // in headline savings.
      const confirmedSavings = highConfidenceItems.reduce(
  (acc, it) => {
    const diff = it.potential_difference;
    return acc + (diff && diff > 0 ? diff : 0);
  },
  0
);
     const mediumDifferences = items
  .filter(it => it.confidence_tier === 'MEDIUM')
  .reduce(
    (acc, it) => {
      const diff = it.potential_difference;
      return acc + (diff && diff > 0 ? diff : 0);
    },
    0
  );

      const currency = items[0]?.user_currency || 'INR';

      let diffTitle = "Verified Price Difference";
      let diffDisplay = fmtMoney(confirmedSavings, currency);
      let diffColor = "inherit";
      let diffSubtitle = "Based on confirmed plan matches";

      if (confirmedSavings > 0) {
        diffColor = "var(--green)";
        diffSubtitle = "Identified against confirmed plan matches";

      } else if (mediumDifferences > 0) {

        diffTitle = "Unconfirmed Price Gap";
        diffDisplay = fmtMoney(mediumDifferences, currency);
        diffColor = "var(--yellow)";
        diffSubtitle = "Plan unconfirmed; excluded from verified savings";

      } else {

        diffSubtitle = "No price differences identified";
      }

      bar.innerHTML = `

        <div class="metric-card">
          <div class="metric-title">Recurring Charges</div>
          <div class="metric-value">${items.length}</div>
          <div class="metric-subtitle">
            ${verifiedCount} high-confidence comparisons
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-title">Monthly Recurring Spend</div>
          <div class="metric-value">
            ${fmtMoney(totalMonthlySpend, currency)}
          </div>
          <div class="metric-subtitle">
            Across detected recurring charges
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-title">Annual Recurring Spend</div>
          <div class="metric-value">
            ${fmtMoney(totalMonthlySpend * 12, currency)}
          </div>
          <div class="metric-subtitle">
            Estimated from monthly recurring charges
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-title">${diffTitle}</div>

          <div class="metric-value" style="color: ${diffColor};">
            ${diffDisplay}
          </div>

          <div class="metric-subtitle">
            ${diffSubtitle}
          </div>
        </div>

      `;

      bar.style.display = 'grid';
      document.getElementById('decisionPanel').style.display = 'block';
    }

    function renderCards(items) {

      const container = document.getElementById('resultsGrid');

      container.innerHTML = '';

      if (items.length === 0) {

        container.innerHTML =
          '<p style="color: var(--text-muted); grid-column: 1 / -1;">No recurring monthly charge patterns were detected.</p>';

        return;
      }

      items.forEach((item, index) => {

        const rep = item;

        const card = document.createElement('div');

        card.className = 'card';

        card.innerHTML = `

          <div>

            <div class="card-header">

              <span class="merchant">
                ${sanitize(item.merchant)}
              </span>

              <span class="tag tag-${sanitize(rep.confidence_tier)}">
                ${sanitize(rep.confidence_tier)}
              </span>

            </div>

            <div class="amount">

              ${fmtMoney(item.user_amount, item.user_currency)}

              <span style="font-size:14px; font-weight:normal; color:var(--text-muted);">
                / ${sanitize(item.cadence)}
              </span>

            </div>

            <div class="detail">
              ${sanitize(rep.decision_reason)}
            </div>

          </div>

          <button class="view-btn" onclick="openDrawer(${index})">
            View Evidence
          </button>

        `;

        container.appendChild(card);
      });
    }

    function openDrawer(index) {

      const item = currentData[index];
      const rep = item;

      const content = document.getElementById('drawerContent');

      // Helper to render gate status
      function renderGate(checked, passed) {

        if (checked === undefined || checked === null) {
          return `<span style="color: var(--text-muted);">NOT RETURNED</span>`;
        }

        if (!checked) {
          return `<span style="color: var(--text-muted);">NOT CHECKED</span>`;
        }

        return passed
          ? `<span class="check-pass">✓ PASS</span>`
          : `<span class="check-fail">✗ MISMATCH</span>`;
      }

      let comparisonHtml = '';

      /*
       * Distinguish:
       * - CACHE
       * - LIVE_SERPAPI
       * - REPLAY
       * - no search
       */
      const provenanceSource = String(
  item.provenance?.source || ''
).toUpperCase();

           let searchStatus;

      if (!rep.search_performed) {
        searchStatus = '— Search not performed';
      } else if (provenanceSource === 'CACHE') {
        searchStatus = '✓ Cached evidence — no new SerpApi search';
      } else if (provenanceSource === 'LIVE_SERPAPI') {
        searchStatus = '✓ New SerpApi search performed';
      } else if (provenanceSource === 'REPLAY') {
        searchStatus = '✓ Replay evidence — no new SerpApi search';
      } else {
        searchStatus = '✓ Search performed';
      }

      const priceStatus = rep.price_extracted
        ? '✓ Price evidence extracted'
        : '— No validated price extracted';

      if (rep.reason_code === 'IDENTITY_UNVERIFIED') {

        comparisonHtml = `

          <div class="drawer-section">

            <h4>Market Comparison</h4>

            <div style="
              background: rgba(100, 116, 139, 0.1);
              border: 1px dashed var(--border);
              padding: 12px;
              border-radius: 6px;
              font-size: 13px;
              color: var(--text-muted);
              line-height: 1.4;
            ">

              <strong>Search not attempted:</strong>
              Merchant identity could not be confirmed locally.
              No external search was made, so no public pricing evidence is available.

            </div>

          </div>

        `;

      } else if (rep.reason_code === 'NO_PRICE_FOUND') {

        comparisonHtml = `

          <div class="drawer-section">

            <h4>Market Comparison</h4>

            <div style="
              background: rgba(100, 116, 139, 0.1);
              border: 1px dashed var(--border);
              padding: 12px;
              border-radius: 6px;
              font-size: 13px;
              color: var(--text-muted);
              line-height: 1.4;
            ">

              <strong>Search completed, price unavailable:</strong>
              Public search was performed, but no subscription price could be extracted
              and validated with high confidence.

            </div>

          </div>

        `;

      } else {

        comparisonHtml = `

          <div class="drawer-section">

            <h4>Market Comparison Validation</h4>

            <div class="drawer-row">
              <span>Currency Gate</span>
              ${renderGate(rep.currency_checked, rep.currency_match)}
            </div>

            <div class="drawer-row">
              <span>Billing Cadence Gate</span>
              ${renderGate(rep.cadence_checked, rep.cadence_match)}
            </div>

            ${!gatesReturned ? `
              <div class="drawer-note" style="margin-top: 8px;">
                Detailed currency and cadence gate results were not returned by the API for this item.
              </div>
            ` : ''}

            <div class="drawer-row">
              <span>Matched Listed Plan</span>
              <span>${sanitize(rep.matched_plan) || 'None Confirmed'}</span>
            </div>

            ${
              rep.potential_difference !== null &&
              rep.potential_difference !== undefined
                ? `

                  <div class="drawer-row">

                    <span>Price Comparison</span>

                    <span style="color: ${
                      Math.abs(rep.potential_difference) <= 0.01
                        ? 'var(--green)'
                        : rep.potential_difference > 0
                          ? 'var(--yellow)'
                          : 'var(--green)'
                    };">

                      ${
                        Math.abs(rep.potential_difference) <= 0.01
                          ? 'Your charge closely matches current pricing'

                          : rep.potential_difference > 0

                            ? `You pay ${
                                fmtMoney(
                                  rep.potential_difference,
                                  item.user_currency
                                )
                              } more than the nearest listed plan`

                            : `You already pay ${
                                fmtMoney(
                                  Math.abs(rep.potential_difference),
                                  item.user_currency
                                )
                              } less than the nearest listed plan`
                      }

                    </span>

                  </div>

                `
                : ''
            }

          </div>

        `;
      }

      content.innerHTML = `

        <div class="drawer-section">

          <h4>Recurring Detection Math</h4>

          <div class="drawer-row">
            <span>Occurrences</span>
            <span>${sanitize(item.occurrences)} transactions</span>
          </div>

          <div class="drawer-row">
            <span>Average Interval</span>
            <span>${sanitize(item.avg_interval)} days</span>
          </div>

          <div class="drawer-row">
            <span>Amount Variation (CV)</span>
            <span>${sanitize(item.amount_variation_pct)}%</span>
          </div>

          <div class="drawer-row">
            <span>Pattern Confidence</span>
            <span>${sanitize(item.recurring_confidence)}%</span>
          </div>

        </div>

        <div class="drawer-section">

          <h4>Evidence Availability</h4>

          <div class="drawer-row">
            <span>Market Search</span>
            <span>${sanitize(searchStatus)}</span>
          </div>

          <div class="drawer-row">
            <span>Price Evidence</span>
            <span>${sanitize(priceStatus)}</span>
          </div>

        </div>

        ${
          item.price_change_detected
            ? `

              <div class="drawer-section">

                <h4>Historical Charge Changes</h4>

                ${
                  item.price_changes?.map(change => `

                    <div class="drawer-row">

                      <span>

                        ${fmtMoney(
                          change.previous_amount,
                          item.user_currency
                        )}

                        →

                        ${fmtMoney(
                          change.current_amount,
                          item.user_currency
                        )}

                      </span>

                      <span>

                        ${fmtMoney(
                          change.change_amount,
                          item.user_currency
                        )}

                        ${
                          change.change_pct !== null
                            ? ` (${
                                change.change_pct > 0 ? '+' : ''
                              }${change.change_pct}%)`
                            : ''
                        }

                      </span>

                    </div>

                  `).join('') || ''
                }

                ${
                  item.amount_history?.length
                    ? `

                      <div class="drawer-note" style="margin-top: 10px;">

                        <strong>Observed charge history:</strong>

                        ${
                          item.amount_history
                            .map(entry =>
                              fmtMoney(
                                entry.amount,
                                item.user_currency
                              )
                            )
                            .join(' → ')
                        }

                      </div>

                    `
                    : ''
                }

                <div class="drawer-note" style="margin-top: 8px;">

                  These are changes observed in the statement's recurring charges.
                  They do not establish the cause of the change or imply an official
                  merchant price change.

                </div>

              </div>

            `
            : ''
        }

        ${comparisonHtml}

        ${
          rep.cheaper_options &&
          rep.cheaper_options.length > 0
            ? `

              <div class="drawer-section">

                <h4>Alternative Listed Tiers</h4>

                ${
                  rep.cheaper_options
                    .map(t => `

                      <div class="drawer-row">

                        <span>

                          ${sanitize(t.tier)}

                          ${
                            t.eligibility
                              ? ' - may require eligibility verification'
                              : ''
                          }

                        </span>

                        <span>

                          ${fmtMoney(
                            t.price,
                            item.user_currency
                          )}

                          (Diff:
                          ${fmtMoney(
                            t.saving,
                            item.user_currency
                          )})

                        </span>

                      </div>

                    `)
                    .join('')
                }

              </div>

            `
            : ''
        }

        <div class="drawer-section">

          <h4>Evidence Source</h4>

          <div class="source-box">
            ${sanitize(item.evidence_note)}
          </div>

        </div>

      `;

      document.getElementById('drawerTitle').innerText =
        `${item.merchant} Evidence`;

      document.getElementById('drawerOverlay').style.display = 'block';

      document
        .getElementById('evidenceDrawer')
        .classList.add('open');
    }

    function closeDrawer() {

      document.getElementById('drawerOverlay').style.display = 'none';

      document
        .getElementById('evidenceDrawer')
        .classList.remove('open');
    }
  