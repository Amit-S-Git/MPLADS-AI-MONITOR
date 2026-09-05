MPLADS AI Monitor - Unified Sidebar Toggle Fix

Replace these files in your project:
- index.html
- projects.html
- alerts.html
- analytics.html
- map.html
- reports.html
- settings.html
- sidebar.css
- style.css

Keep your existing backend/data files unchanged:
- app.py
- projects_data.json
- reports_data.json
- report_style.css
- settings.css
- login.html

What was fixed:
1. The hamburger/sidebar toggle is now present on every internal page.
2. The toggle has the same size, position, icon, border, shadow and behavior as the Dashboard.
3. Reports-specific CSS can no longer hide the toggle.
4. Page headings reserve space for the toggle, so Settings/Reports/etc. do not overlap it.
5. When the sidebar collapses, the toggle moves to the left and the heading spacing resets correctly.
6. The sidebar still has the same 8 items everywhere: Home, Dashboard, Projects, Risk Alerts, Analytics, Map View, Reports, Settings.

After replacing the files, hard refresh the browser with Ctrl + Shift + R.
