#ui/assets/js/map_utils.js

function zoomToFit() {
    // Get map instance
    var map = document.querySelector('#map');
    var bounds = new L.LatLngBounds();
    
    // Get all markers
    map.eachLayer(function(layer) {
        if (layer instanceof L.Marker) {
            bounds.extend(layer.getLatLng());
        }
    });
    
    // Fit bounds with padding
    map.fitBounds(bounds, {padding: [50, 50]});
}

function toggleAllRoutes() {
    // Get map instance
    var map = document.querySelector('#map');
    var routeLayers = [];
    
    // Find all route layers
    map.eachLayer(function(layer) {
        if (layer instanceof L.Polyline) {
            routeLayers.push(layer);
        }
    });
    
    // Toggle visibility
    var visible = routeLayers[0].options.opacity > 0;
    routeLayers.forEach(function(layer) {
        layer.setStyle({opacity: visible ? 0 : 0.7});
    });
}

// ui/assets/css/style.css

/* Map styles */
.map-controls {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 1000;
    background: white;
    padding: 10px;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.map-controls button {
    display: block;
    width: 100%;
    padding: 8px 12px;
    margin-bottom: 5px;
    border: none;
    border-radius: 4px;
    background: #2563eb;
    color: white;
    cursor: pointer;
    font-size: 14px;
}

.map-controls button:hover {
    background: #1d4ed8;
}

/* Popup styles */
.popup-content {
    padding: 10px;
    max-width: 200px;
}

.popup-content h4 {
    margin: 0 0 8px 0;
    color: #1f2937;
}

.popup-content p {
    margin: 4px 0;
    color: #4b5563;
}

/* Metrics panel styles */
.metric-card {
    background: white;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.metric-value {
    font-size: 24px;
    font-weight: 600;
    color: #2563eb;
}

.metric-label {
    font-size: 14px;
    color: #6b7280;
}

/* Table styles */
.table-filters {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
}

.filter-group {
    flex: 1;
}

.filter-label {
    font-size: 14px;
    color: #4b5563;
    margin-bottom: 4px;
}

/* Chart styles */
.chart-container {
    background: white;
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 16px;