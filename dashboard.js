let charts = {};

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔄 Initializing dashboard...');
    
    // Check if required elements exist
    if (!document.getElementById('predictionForm')) {
        console.error('❌ predictionForm not found!');
    }
    if (!document.getElementById('clearHistory')) {
        console.error('❌ clearHistory button not found!');
    }
    
    loadDashboardData();
    document.getElementById('predictionForm')?.addEventListener('submit', handlePrediction);
    document.getElementById('clearHistory')?.addEventListener('click', clearHistory);
    setInterval(loadDashboardData, 30000);
});

async function loadDashboardData() {
    try {
        console.log('📡 Fetching dashboard data...');
        const response = await fetch('/api/stats');
        const data = await response.json();
        console.log('📊 Dashboard data received:', data);
        
        updateStatCards(data);
        updateCharts(data);
        updateRecentPredictions(data.recent_predictions);
    } catch (error) {
        console.error('❌ Error loading dashboard data:', error);
    }
}

function updateStatCards(data) {
    const totalEl = document.getElementById('totalPredictions');
    if (totalEl) totalEl.textContent = data.total_predictions || 0;
    
    if (data.avg_confidence_by_model?.length > 0) {
        const avgConf = data.avg_confidence_by_model.reduce((sum, item) => sum + item.avg_confidence, 0) / data.avg_confidence_by_model.length;
        document.getElementById('avgConfidence')?.textContent = (avgConf * 100).toFixed(1) + '%';
    }
    
    document.getElementById('modelsUsed')?.textContent = data.predictions_by_model?.length || 0;
    
    if (data.predictions_by_class?.length > 0) {
        const topPred = data.predictions_by_class.reduce((max, item) => item.count > max.count ? item : max, data.predictions_by_class[0]);
        document.getElementById('topPrediction')?.textContent = topPred._id.charAt(0).toUpperCase() + topPred._id.slice(1);
    }
}

function updateCharts(data) {
    console.log('📈 Updating charts with data:', data);
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('❌ Chart.js not loaded! Add <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>');
        return;
    }
    
    if (data.predictions_by_class?.length > 0) {
        const labels = data.predictions_by_class.map(item => item._id.charAt(0).toUpperCase() + item._id.slice(1));
        const counts = data.predictions_by_class.map(item => item.count);
        createOrUpdateChart('predictionsByClass', {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Predictions',
                    data: counts,
                    backgroundColor: ['rgba(102, 126, 234, 0.8)', 'rgba(118, 75, 162, 0.8)', 'rgba(237, 100, 166, 0.8)']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
    }
    
    // Similar updates for other charts...
    if (data.predictions_by_model?.length > 0) {
        const labels = data.predictions_by_model.map(item => item._id.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()));
        const counts = data.predictions_by_model.map(item => item.count);
        createOrUpdateChart('predictionsByModel', {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{ data: counts, backgroundColor: ['rgba(102, 126, 234, 0.8)', 'rgba(118, 75, 162, 0.8)'] }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }
}

function createOrUpdateChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`❌ Canvas '${canvasId}' not found!`);
        return;
    }
    
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }
    charts[canvasId] = new Chart(canvas.getContext('2d'), config);
    console.log(`✅ Chart '${canvasId}' updated`);
}

async function handlePrediction(e) {
    e.preventDefault();
    console.log('🔮 Making prediction...');
    
    const features = [
        parseFloat(document.getElementById('sepal_length')?.value || 0),
        parseFloat(document.getElementById('sepal_width')?.value || 0),
        parseFloat(document.getElementById('petal_length')?.value || 0),
        parseFloat(document.getElementById('petal_width')?.value || 0)
    ];
    const model = document.getElementById('model')?.value || 'logistic_regression';
    
    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ features, model })
        });
        const data = await response.json();
        
        if (response.ok) {
            console.log('✅ Prediction successful:', data);
            const resultDiv = document.getElementById('predictionResult');
            if (resultDiv) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `
                    <strong>Prediction:</strong> ${data.prediction.toUpperCase()}<br>
                    <strong>Confidence:</strong> ${(data.confidence * 100).toFixed(2)}%<br>
                    <strong>Model:</strong> ${data.model_used.replace('_', ' ')}
                `;
            }
            // **FIXED: Proper delay for MongoDB write**
            setTimeout(() => {
                console.log('🔄 Refreshing dashboard after prediction...');
                loadDashboardData();
            }, 300); // Increased to 300ms for MongoDB write
        }
    } catch (error) {
        console.error('❌ Prediction failed:', error);
        alert('Prediction failed: ' + error.message);
    }
}
