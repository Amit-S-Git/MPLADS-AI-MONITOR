MPLADS AI Monitor - Render deployment fix

Your Render build failed because requirements.txt was missing from the repository root.

1. Upload requirements.txt to the TOP LEVEL of your GitHub repository, beside app.py.
2. Upload .python-version to the TOP LEVEL too (recommended; pins Python 3.12).
3. In Render Settings use:
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn app:app
   Root Directory: leave blank if app.py is at repository root.
4. Commit the files to the main branch.
5. In Render choose Manual Deploy > Deploy latest commit (or Clear build cache & deploy if needed).

Expected GitHub root:
app.py
requirements.txt
.python-version
index.html
...
