MPLADS INTEGRATED PUBLIC/PRIVATE DASHBOARD PATCH

This fixes the "public dashboard opens as a separate website/page" problem.

COPY/REPLACE ONLY THESE FILES IN YOUR EXISTING PROJECT FOLDER:
1. app.py                  -> replace
2. index.html              -> replace
3. login.html              -> replace
4. public_dashboard.css    -> add
5. public_dashboard.js     -> add

DO NOT replace style.css, sidebar.css, home.html, projects.html, alerts.html, analytics.html, map.html, reports.html, settings.html, JSON files or images.

HOW IT WORKS
- Home remains your existing home.html.
- Clicking Dashboard still opens index.html.
- If NOT logged in, index.html shows the searchable PUBLIC dashboard only.
- If logged in, the SAME index.html shows your EXISTING officer dashboard exactly as before.
- Successful login redirects back to index.html, so the officer dashboard appears automatically.
- Projects/Risk Alerts/Analytics/Map/Reports/Settings remain the existing protected pages.

IMPORTANT
Run: py app.py
Open the Flask address shown in Terminal (normally http://127.0.0.1:5002/ with this app.py).
Do not use VS Code Live Server because /api/public-projects requires Flask.

The current sample data does not contain a real constituency field. app.py supplies a small display mapping for the prototype without changing projects_data.json.
