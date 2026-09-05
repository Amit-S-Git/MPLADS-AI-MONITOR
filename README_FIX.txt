MPLADS FUNCTION FIX PATCH

Why Analytics, Risk Alerts and Map were failing:
1. Older page files call http://127.0.0.1:5000 while your Flask app now runs on port 5002.
2. map.html tried to execute Leaflet map code before Leaflet JavaScript had finished loading.
3. /api/alerts returns the risk reasons as `reasons`, while alerts.html expected `risk_reasons`.

WHAT TO REPLACE
- analytics.html
- alerts.html
- map.html
- projects.html

DO NOT replace app.py, index.html, login.html, CSS, JSON data, reports, settings, or images for this fix.

The fixed pages use window.location.origin, so they automatically work on port 5002, 5000, Render, or another host.
They also fall back to projects_data.json if an API read temporarily fails.

Restart Flask after copying the files:
  Ctrl+C
  py app.py

Then hard refresh the browser:
  Ctrl+F5

Test:
  http://127.0.0.1:5002/api/projects
  http://127.0.0.1:5002/api/dashboard
  http://127.0.0.1:5002/api/alerts

Each should show JSON in the browser.
