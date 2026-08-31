const API_URL = "http://127.0.0.1:8001";

const RESOURCE_GROUPS = [
    {
        title: "Food",
        items: [
            "Dry ration kits",
            "Cooked meal distribution points",
            "Emergency nutrition packets"
        ]
    },
    {
        title: "Water",
        items: [
            "Safe drinking water tanks",
            "Water purification units",
            "Mobile water supply trucks"
        ]
    },
    {
        title: "Shelter",
        items: [
            "School and community shelters",
            "Temporary tents",
            "Family relief camps"
        ]
    },
    {
        title: "Hospitals",
        items: [
            "Primary health centers",
            "Mobile medical units",
            "Emergency ambulance support"
        ]
    }
];

let relocationRoute = null;
let relocationMarkers = [];

// ============================================================
// CREATE MAP
// ============================================================

const map = L.map("map").setView([26.2, 92.9], 7);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);


// ============================================================
// RISK COLORS
// ============================================================

function getRiskColor(riskLevel) {

    if (riskLevel === "HIGH") {
        return "#ef4444";
    }

    if (riskLevel === "MEDIUM") {
        return "#f59e0b";
    }

    return "#22c55e";
}


// ============================================================
// DISTRICT STYLE
// ============================================================

function districtStyle(feature) {

    const riskLevel = feature.properties.risk_level;

    return {
        fillColor: getRiskColor(riskLevel),
        weight: 1,
        opacity: 1,
        color: "#333",
        fillOpacity: 0.65
    };
}


// ============================================================
// HIGHLIGHT DISTRICT
// ============================================================

function highlightDistrict(event) {

    const layer = event.target;

    layer.setStyle({
        weight: 3,
        color: "#111",
        fillOpacity: 0.85
    });

    layer.bringToFront();
}


// ============================================================
// RESET DISTRICT
// ============================================================

function resetDistrict(event) {

    if (geojsonLayer) {
        geojsonLayer.resetStyle(event.target);
    }
}


// ============================================================
// FORMAT NUMBERS
// ============================================================

function formatNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        Number.isNaN(Number(value))
    ) {
        return "No data";
    }

    return Number(value).toLocaleString("en-IN");
}


// ============================================================
// FORMAT DECIMAL
// ============================================================

function formatDecimal(value) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        Number.isNaN(Number(value))
    ) {
        return "No data";
    }

    return Number(value).toFixed(2);
}


// ============================================================
// FORMAT RISK SCORE
// ============================================================

function formatRiskScore(value) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        Number.isNaN(Number(value))
    ) {
        return "No data";
    }

    return Number(value).toFixed(3);
}


// ============================================================
// SHOW DISTRICT INFORMATION
// ============================================================

function getRiskPriority(riskLevel) {

    if (riskLevel === "HIGH") return 3;
    if (riskLevel === "MEDIUM") return 2;
    return 1;
}


function flattenCoordinates(coords) {

    const flattened = [];

    for (const item of coords) {

        if (Array.isArray(item) && item.length === 2 &&
            typeof item[0] === "number" &&
            typeof item[1] === "number") {
            flattened.push(item);
        }

        else if (Array.isArray(item)) {
            flattened.push(...flattenCoordinates(item));
        }
    }

    return flattened;
}


function getDistrictCentroid(feature) {

    if (!feature || !feature.geometry) {
        return null;
    }

    const geometry = feature.geometry;
    const allCoords = [];

    if (geometry.type === "Polygon") {
        allCoords.push(...flattenCoordinates(geometry.coordinates));
    }

    else if (geometry.type === "MultiPolygon") {
        for (const polygon of geometry.coordinates) {
            allCoords.push(...flattenCoordinates(polygon));
        }
    }

    if (!allCoords.length) {
        return null;
    }

    let latSum = 0;
    let lngSum = 0;

    for (const [lng, lat] of allCoords) {
        latSum += lat;
        lngSum += lng;
    }

    return {
        lat: latSum / allCoords.length,
        lng: lngSum / allCoords.length
    };
}


function getRouteResources(district, riskLevel) {

    const baseResources = {
        Food: [
            `${district} relief kitchens`,
            "Family ration kits",
            "Ready-to-eat nutrition packs"
        ],
        Water: [
            "Safe drinking water points",
            "Mobile water tankers",
            "Purification tablets and filters"
        ],
        Shelter: [
            "Temporary community shelters",
            "School shelter centers",
            "Emergency tents and bedding"
        ],
        Hospitals: [
            "Primary health center access",
            "Emergency ambulance deployment",
            "Mobile medical outreach teams"
        ]
    };

    if (riskLevel === "HIGH") {
        baseResources.Food.push("Priority dry ration distribution");
        baseResources.Water.push("24x7 water refilling points");
        baseResources.Shelter.push("Transit evacuation centers");
        baseResources.Hospitals.push("Critical trauma response support");
    }

    return baseResources;
}


function clearRelocationRoute() {

    if (relocationRoute) {
        map.removeLayer(relocationRoute);
        relocationRoute = null;
    }

    for (const marker of relocationMarkers) {
        map.removeLayer(marker);
    }

    relocationMarkers = [];
}


function showRelocationRoute(fromFeature, toFeature) {

    if (!fromFeature || !toFeature) {
        return;
    }

    clearRelocationRoute();

    const from = getDistrictCentroid(fromFeature);
    const to = getDistrictCentroid(toFeature);

    if (!from || !to) {
        return;
    }

    relocationRoute = L.polyline(
        [
            [from.lat, from.lng],
            [to.lat, to.lng]
        ],
        {
            color: "#2563eb",
            weight: 4,
            opacity: 0.9,
            dashArray: "10, 10"
        }
    ).addTo(map);

    const fromMarker = L.circleMarker([from.lat, from.lng], {
        radius: 7,
        color: "#dc2626",
        fillColor: "#fca5a5",
        fillOpacity: 1
    }).bindPopup(`Red zone: ${fromFeature.properties.district}`).addTo(map);

    const toMarker = L.circleMarker([to.lat, to.lng], {
        radius: 7,
        color: "#16a34a",
        fillColor: "#86efac",
        fillOpacity: 1
    }).bindPopup(`Safe zone: ${toFeature.properties.district}`).addTo(map);

    relocationMarkers = [fromMarker, toMarker];

    const bounds = L.latLngBounds([
        [from.lat, from.lng],
        [to.lat, to.lng]
    ]);

    map.fitBounds(bounds, { padding: [50, 50] });
}


function suggestSafeRelocation(feature, districtFeatures) {

    const currentRisk = feature.properties.risk_level || "UNKNOWN";

    if (currentRisk === "UNKNOWN") {
        return null;
    }

    const fromCentre = getDistrictCentroid(feature);

    if (!fromCentre) {
        return null;
    }

    const candidates = districtFeatures
        .filter(candidate =>
            candidate.properties.district !== feature.properties.district
        )
        .map(candidate => {
            const candidateCentre = getDistrictCentroid(candidate);

            if (!candidateCentre) {
                return null;
            }

            const distanceKm = Math.round(
                Math.hypot(
                    (candidateCentre.lat - fromCentre.lat) * 111,
                    (candidateCentre.lng - fromCentre.lng) * 111
                )
            );

            const candidateRisk = candidate.properties.risk_level || "LOW";
            const riskScore = getRiskPriority(candidateRisk);
            const currentPriority = getRiskPriority(currentRisk);

            const suitability = (
                currentPriority === 3
                    ? riskScore === 1 ? 35 : 15
                    : riskScore === 1 ? 25 : 10
            ) - Math.min(distanceKm / 50, 20);

            return {
                ...candidate,
                distanceKm,
                suitability
            };
        })
        .filter(Boolean)
        .sort((a, b) => b.suitability - a.suitability);

    if (!candidates.length) {
        return null;
    }

    const target = candidates[0];

    return {
        targetDistrict: target.properties.district,
        targetRisk: target.properties.risk_level,
        distanceKm: target.distanceKm,
        resources: getRouteResources(feature.properties.district, currentRisk),
        routeSummary: `${feature.properties.district} → ${target.properties.district} via the safest available corridor.`
    };
}


function showDistrictInfo(feature, layer) {

    layer.on("click", function () {

        const p = feature.properties;

        const district =
            p.district || "Unknown District";

        const riskLevel =
            p.risk_level || "UNKNOWN";

        const riskClass =
            riskLevel.toLowerCase();

        const population =
            p.population !== undefined &&
            p.population !== null
                ? formatNumber(p.population)
                : "No data";

        const ruralPopulation =
            p.rural_population !== undefined &&
            p.rural_population !== null
                ? formatNumber(p.rural_population)
                : "No data";

        const urbanPopulation =
            p.urban_population !== undefined &&
            p.urban_population !== null
                ? formatNumber(p.urban_population)
                : "No data";

        const panel = document.getElementById("district-panel");

        if (!panel) {
            console.error("District panel not found in index.html");
            return;
        }

        const districtFeatures = geojsonLayer
            ? geojsonLayer.toGeoJSON().features
            : [];

        const relocation = suggestSafeRelocation(feature, districtFeatures);

        if (relocation) {
            showRelocationRoute(feature, districtFeatures.find(candidate =>
                candidate.properties.district === relocation.targetDistrict
            ));
        }

        const resourceHtml = relocation ? `
            <div class="info-section route-section">
                <h3>🛣️ Reallocation Route</h3>
                <div class="route-card">
                    <div class="route-pill">Best safe zone</div>
                    <div class="route-heading">${district} → ${relocation.targetDistrict}</div>
                    <p>${relocation.routeSummary}</p>
                    <div class="route-metrics">
                        <span>Distance: ${relocation.distanceKm} km</span>
                        <span>Destination risk: ${relocation.targetRisk}</span>
                    </div>
                </div>
            </div>

            <div class="info-section">
                <h3>📦 Relief Resources</h3>
                <div class="resource-stack">
                    ${RESOURCE_GROUPS.map(group => `
                        <div class="resource-group">
                            <h4>${group.title}</h4>
                            <ul>
                                ${(relocation.resources[group.title] || group.items).map(item => `<li>${item}</li>`).join("")}
                            </ul>
                        </div>
                    `).join("")}
                </div>
            </div>
        ` : "";

        panel.innerHTML = `

            <div class="district-panel-header">

                <div>

                    <div class="panel-label">
                        ASSAM DISTRICT
                    </div>

                    <h2>
                        ${district}
                    </h2>

                </div>

                <button
                    class="close-panel"
                    onclick="closeDistrictPanel()"
                    aria-label="Close"
                >
                    ×
                </button>

            </div>


            <div class="risk-banner ${riskClass}">

                <div>

                    <span class="risk-label">
                        RISK LEVEL
                    </span>

                    <strong>
                        ${riskLevel}
                    </strong>

                </div>


                <div class="risk-score">

                    <span>
                        Risk Score
                    </span>

                    <strong>
                        ${formatRiskScore(p.risk_score)}
                    </strong>

                </div>

            </div>


            <div class="info-section">

                <h3>
                    👥 Population
                </h3>

                <div class="info-grid">

                    <div class="info-card">
                        <span>Total Population</span>
                        <strong>${population}</strong>
                    </div>

                    <div class="info-card">
                        <span>Rural Population</span>
                        <strong>${ruralPopulation}</strong>
                    </div>

                    <div class="info-card">
                        <span>Urban Population</span>
                        <strong>${urbanPopulation}</strong>
                    </div>

                </div>

            </div>


            <div class="info-section">

                <h3>
                    🌊 Flood History
                </h3>

                <div class="info-grid">

                    <div class="info-card">
                        <span>Flood Events</span>
                        <strong>${formatNumber(p.flood_events)}</strong>
                    </div>

                    <div class="info-card">
                        <span>Fatalities</span>
                        <strong>${formatNumber(p.fatalities)}</strong>
                    </div>

                    <div class="info-card">
                        <span>Injured</span>
                        <strong>${formatNumber(p.injured)}</strong>
                    </div>

                    <div class="info-card">
                        <span>Displaced</span>
                        <strong>${formatNumber(p.displaced)}</strong>
                    </div>

                </div>

            </div>


            <div class="info-section">

                <h3>
                    🌎 Earthquake History
                </h3>

                <div class="info-grid">

                    <div class="info-card">
                        <span>Earthquake Events</span>
                        <strong>${formatNumber(p.earthquake_events)}</strong>
                    </div>

                    <div class="info-card">
                        <span>Maximum Magnitude</span>
                        <strong>${formatDecimal(p.max_earthquake_magnitude)}</strong>
                    </div>

                    <div class="info-card">
                        <span>Average Magnitude</span>
                        <strong>${formatDecimal(p.avg_earthquake_magnitude)}</strong>
                    </div>

                </div>

            </div>

            ${resourceHtml}

        `;

        panel.classList.add("active");

    });
}


// ============================================================
// DISTRICT EVENTS
// ============================================================

function onEachDistrict(feature, layer) {

    layer.on({
        mouseover: highlightDistrict,
        mouseout: resetDistrict
    });

    showDistrictInfo(feature, layer);
}


// ============================================================
// GEOJSON LAYER
// ============================================================

let geojsonLayer = null;


// ============================================================
// CLOSE DISTRICT PANEL
// ============================================================

function closeDistrictPanel() {

    const panel =
        document.getElementById("district-panel");

    if (panel) {
        panel.classList.remove("active");
    }
}


// ============================================================
// LOAD ZONES
// ============================================================

async function loadZones() {

    try {

        console.log(
            "Loading Assam risk zones..."
        );


        const response =
            await fetch(`${API_URL}/zones`);


        console.log(
            "API status:",
            response.status
        );


        if (!response.ok) {

            throw new Error(
                `API returned HTTP ${response.status}`
            );
        }


        let data =
            await response.json();


        // ----------------------------------------------------
        // Handle JSON string if necessary
        // ----------------------------------------------------

        if (typeof data === "string") {

            console.log(
                "API returned GeoJSON as string. Parsing..."
            );

            data = JSON.parse(data);
        }


        console.log(
            "Zones loaded:",
            data
        );


        console.log(
            "Number of districts:",
            data.features
                ? data.features.length
                : 0
        );


        // ----------------------------------------------------
        // Validate GeoJSON
        // ----------------------------------------------------

        if (
            !data ||
            data.type !== "FeatureCollection" ||
            !Array.isArray(data.features)
        ) {

            throw new Error(
                "API did not return valid GeoJSON."
            );
        }


        // ----------------------------------------------------
        // Remove previous layer
        // ----------------------------------------------------

        if (geojsonLayer) {

            map.removeLayer(
                geojsonLayer
            );

            geojsonLayer = null;
        }


        // ----------------------------------------------------
        // Create district polygons
        // ----------------------------------------------------

        geojsonLayer =
            L.geoJSON(
                data,
                {
                    style: districtStyle,
                    onEachFeature: onEachDistrict
                }
            ).addTo(map);


        // ----------------------------------------------------
        // Check districts
        // ----------------------------------------------------

        if (
            geojsonLayer.getLayers().length === 0
        ) {

            throw new Error(
                "No district polygons found."
            );
        }


        // ----------------------------------------------------
        // Zoom to Assam
        // ----------------------------------------------------

        map.fitBounds(
            geojsonLayer.getBounds(),
            {
                padding: [20, 20]
            }
        );


        console.log(
            "Map loaded successfully.",
            geojsonLayer.getLayers().length,
            "districts"
        );

    }

    catch (error) {

        console.error(
            "Failed to load zones:",
            error
        );


        alert(
            "Could not load disaster zones.\n\n" +
            "Make sure the FastAPI server is running."
        );
    }
}


// ============================================================
// POPULATION REALLOCATION DASHBOARD
// ============================================================

async function loadPopulationReallocationDashboard() {

    const summaryEl = document.getElementById("reallocation-summary");
    const compareEl = document.getElementById("reallocation-compare");
    const planEl = document.getElementById("reallocation-plan");
    const resourcesEl = document.getElementById("reallocation-resources");

    if (!summaryEl || !compareEl || !planEl || !resourcesEl) {
        return;
    }

    try {
        const safeZonesResponse = await fetch(`${API_URL}/api/population-reallocation/safe-zones`);
        const safeZonesData = safeZonesResponse.ok ? await safeZonesResponse.json() : { safe_zones: [] };

        const payload = {
            red_zone_name: "Red Zone A",
            red_zone_population: 20000,
            safe_zones: safeZonesData.safe_zones || []
        };

        const analyzeResponse = await fetch(`${API_URL}/api/population-reallocation/analyze`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!analyzeResponse.ok) {
            throw new Error("Allocation API unavailable");
        }

        const result = await analyzeResponse.json();
        const allocation = result.allocation || { allocations: [], remaining_population: 0, total_allocated: 0 };

        summaryEl.innerHTML = `
            <div class="card">
                <span class="label">Red Zones</span>
                <div class="value">1</div>
            </div>
            <div class="card">
                <span class="label">Affected Population</span>
                <div class="value">${formatNumber(result.total_affected_population || 20000)}</div>
            </div>
            <div class="card">
                <span class="label">Population Requiring Evacuation</span>
                <div class="value">${formatNumber(result.total_affected_population || 20000)}</div>
            </div>
            <div class="card">
                <span class="label">Critical Zones</span>
                <div class="value">${allocation.insufficient_capacity ? "Capacity Alert" : "1"}</div>
            </div>
        `;

        compareEl.innerHTML = `
            <div class="item-card">
                <h3>Safe Zone Comparison</h3>
                <ul class="metric-list">
                    ${(result.safe_zone_ranking || []).map(zone => `
                        <li>
                            <strong>${zone.name}</strong> — Distance ${zone.distance_km || 0} km, Capacity ${formatNumber(zone.available_capacity || 0)}, Suitability ${zone.overall_suitability_score || 0}%
                        </li>
                    `).join("")}
                </ul>
            </div>
        `;

        planEl.innerHTML = `
            <div class="item-card">
                <h3>Allocation Plan</h3>
                <ul class="metric-list">
                    ${(allocation.allocations || []).map(item => `
                        <li>${item.safe_zone} → ${item.assigned_population} people → ${item.travel_time_minutes || 0} min travel</li>
                    `).join("")}
                </ul>
                ${allocation.warning ? `<div class="warning-banner">${allocation.warning}</div>` : ""}
            </div>
        `;

        resourcesEl.innerHTML = `
            <div class="item-card">
                <h3>Resource Requirements</h3>
                <ul class="metric-list">
                    ${(allocation.allocations || []).map(item => `
                        <li>
                            <strong>${item.safe_zone}</strong>: Food ${(item.assigned_population * 0.75).toFixed(0)} kg/day, Water ${(item.assigned_population * 4.5).toFixed(0)} L/day, Shelter ${(item.assigned_population * 0.32).toFixed(0)} spaces
                        </li>
                    `).join("")}
                </ul>
            </div>
        `;

    } catch (error) {
        console.error("Failed to load reallocation dashboard:", error);
        summaryEl.innerHTML = `
            <div class="card">
                <span class="label">Reallocation</span>
                <div class="value">Unavailable</div>
            </div>
        `;
        compareEl.innerHTML = "";
        planEl.innerHTML = "";
        resourcesEl.innerHTML = "";
    }
}


// ============================================================
// START APPLICATION
// ============================================================

loadZones();
loadPopulationReallocationDashboard();