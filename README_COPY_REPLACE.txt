MPLADS MINIMAL PUBLIC DASHBOARD PATCH
=====================================

This patch makes ONLY the requested flow change:

1. BEFORE LOGIN
   /  -> public read-only dashboard
   Visitors can search/filter projects by:
   - State
   - District
   - Constituency
   - Status (Ongoing / Completed / Delayed)
   - Project name / Project ID

2. AFTER LOGIN
   /dashboard -> your existing index.html officer dashboard
   Your existing detailed dashboard UI is NOT included or redesigned by this patch.

FILES TO COPY INTO YOUR EXISTING PROJECT FOLDER
----------------------------------------------
REPLACE:
- app.py
- login.html

ADD / REPLACE THESE NEW PUBLIC FILES:
- public_dashboard.html
- public_dashboard.css
- public_dashboard.js

DO NOT REPLACE:
- index.html
- style.css
- sidebar.css
- projects.html
- alerts.html
- analytics.html
- map.html
- reports.html
- settings.html
- script.js
- projects_data.json
- reports_data.json
- images/

IMPORTANT
---------
Run through Flask, not Live Server:

  py app.py

Then open the port shown by Flask (this app defaults to 5002):

  http://127.0.0.1:5002/

Expected flow:
  / -> Public dashboard -> Officer Login -> /login -> /dashboard -> existing officer dashboard

The public page uses /api/public-projects, which returns only public-facing fields.
The existing /api/projects and all officer-side APIs remain unchanged.

Current project data does not contain a constituency field, so app.py maps:
Jaipur -> Jaipur
Kota -> Kota-Bundi
Ajmer -> Ajmer
Jodhpur -> Jodhpur
Udaipur -> Udaipur

This mapping affects only the public display and can later be replaced by real constituency data.
