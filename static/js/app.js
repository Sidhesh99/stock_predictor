let priceChart = null;

/* ── send request, receive JSON, render everything ── */
async function makePrediction() {
    const stock     = document.getElementById('stock').value;
    const startDate = document.getElementById('start_date').value;
    const endDate   = document.getElementById('end_date').value;

    // show loader, hide old results
    document.getElementById('loading').style.display    = 'block';
    document.getElementById('error').style.display     = 'none';
    document.getElementById('chartSection').style.display = 'none';
    document.getElementById('results').style.display   = 'none';

    try {
        const res  = await fetch('/predict', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ stock, start_date: startDate, end_date: endDate })
        });
        const data = await res.json();

        document.getElementById('loading').style.display = 'none';

        if (!data.success) { showError(data.error); return; }

        displayResults(data);
        drawChart(data);

    } catch (e) {
        document.getElementById('loading').style.display = 'none';
        showError('Network error: ' + e.message);
    }
}

/* ── error banner ─────────────────────────────── */
function showError(msg) {
    const el = document.getElementById('error');
    el.textContent = msg;
    el.style.display = 'block';
}

/* ── populate result cards ────────────────────── */
function displayResults(data) {
    document.getElementById('currentPrice').textContent   = '₹' + data.current_price.toFixed(2);
    document.getElementById('predictedPrice').textContent = '₹' + data.predicted_price.toFixed(2);

    const changeEl = document.getElementById('priceChange');
    const ch       = data.price_change;
    changeEl.textContent = (ch >= 0 ? '+' : '') + ch.toFixed(2) + '%';
    changeEl.style.color = ch >= 0 ? '#10b981' : '#ef4444';

    const decEl = document.getElementById('decision');
    decEl.textContent = data.decision;
    decEl.className   = 'decision ' + data.decision;

    document.getElementById('confidence').textContent = data.confidence + '%';
    document.getElementById('results').style.display  = 'block';
}

/* ── chart ────────────────────────────────────── */
function drawChart(data) {
    // update heading
    document.getElementById('chartTitle').textContent = data.stock_name;

    const ctx = document.getElementById('priceChart').getContext('2d');
    if (priceChart) priceChart.destroy();

    const labels = [...data.dates];
    const prices = [...data.historical_prices];

    // add one extra label for the predicted dot
    const lastDate = new Date(labels[labels.length - 1]);
    lastDate.setDate(lastDate.getDate() + 1);
    labels.push(lastDate.toISOString().split('T')[0]);

    // historical dataset  – every point filled
    const histDataset = prices.map((p, i) => ({ x: labels[i], y: p }));

    // predicted dataset  – only the very last point
    const predDataset = Array(prices.length).fill(null);
    predDataset.push(data.predicted_price);

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label:           'Historical Price',
                    data:            histDataset,
                    borderColor:     '#667eea',
                    backgroundColor: 'rgba(102,126,234,0.08)',
                    borderWidth:     2,
                    fill:            true,
                    tension:         0.1,
                    pointRadius:     0,
                    pointHoverRadius: 5
                },
                {
                    label:           'Predicted Price',
                    data:            predDataset,
                    borderColor:     '#10b981',
                    backgroundColor: '#10b981',
                    borderWidth:     0,
                    pointRadius:     9,
                    pointHoverRadius: 11,
                    pointStyle:      'circle',
                    showLine:        false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display:  true,
                    position: 'top',
                    labels:   { usePointStyle: true, padding: 20, font: { size: 13, weight: 'bold' } }
                },
                tooltip: {
                    callbacks: {
                        label(ctx) {
                            return ctx.dataset.label + ': ₹' + (ctx.parsed.y !== null ? ctx.parsed.y.toFixed(2) : '—');
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Date',  font: { size: 14, weight: 'bold' } },
                    ticks: { maxTicksLimit: 10, autoSkip: true }
                },
                y: {
                    title: { display: true, text: 'Price (₹)', font: { size: 14, weight: 'bold' } },
                    ticks: { callback: v => '₹' + v.toFixed(0) }
                }
            }
        }
    });

    document.getElementById('chartSection').style.display = 'block';
}
