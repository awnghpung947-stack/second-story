# Second Story — Clothing Resale Platform

A beginner-friendly local marketplace where members can list pre-loved clothing, browse available items, and send purchase requests to sellers. One registered account can act as both buyer and seller.
## Technology

- Python 3 and Flask for server-side pages and form handling
- SQLite for a small local database (created automatically as `clothing_resale.db`)
- HTML templates and plain CSS
- Werkzeug password hashing and secure upload helpers

Flask replaces the PHP backend from the original project brief. SQLite keeps local setup simple: there is no separate MySQL server to configure. You do not need XAMPP for this version.

## Features

- Account registration, login, logout, and profile page
- Password hashing, session checks, role-protected admin, and CSRF tokens
- Clothing listings with image uploads, editing, and seller-only deletion
- Search, category, size, and price filters
- Buyer requests and seller accept/reject workflow; accepted items become sold
- Pending-request badge in the navigation so sellers notice new requests
- The seller's mobile number is revealed to the buyer only after the seller accepts; an accepted buyer's number is also shown to the seller
- Admin overview of users, requests, and listings
- Responsive marketplace styling and empty states

## Folder structure

```text
app.py                  Flask application and database initialization
requirements.txt        Python dependency
clothing_resale.db      Created on first run (not committed)
templates/              Reusable HTML templates
static/css/style.css    Responsive styling
uploads/                Uploaded clothing photographs
```

## Requirements and start-up

Install Python 3.10 or newer. Open PowerShell in this project folder and run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.venv\Scripts\python.exe app.py` without activation.

Open **http://127.0.0.1:5000/** in your browser. Stop the local server with Ctrl+C. The database tables are created on app startup.

## First use

1. Choose **Join us** and create a regular account.
2. Log in and choose **Sell an item** to add a clothing listing and photo (JPG, PNG, or WebP, at most 5 MB).
3. Register a second account in a private browser window or after logging out; browse and request the listed item.
4. Log back in as the seller, open **Seller requests**, then accept or reject the pending request. Accepting the request marks the item sold and reveals your mobile number to that buyer on their **My requests** page and the item page.

The app does not collect payments or arrange delivery. Buyer and seller coordinate the handover directly.

## Make an administrator

There is no public/default admin account. Register the account first, stop the Flask server, then open `clothing_resale.db` with a SQLite viewer such as DB Browser for SQLite. In the `users` table, change that account's `role` value from `user` to `admin`, save, and restart the app. The admin page is then available from the navigation bar. Never change roles through public forms.

Alternatively, if the `sqlite3` command line is installed, use:

```sql
UPDATE users SET role='admin' WHERE email='your-email@example.com';
```

## Configuration and safety notes

Set a private random `SECRET_KEY` environment variable before running the app outside a local demonstration. The fallback key in `app.py` is for local development only. Images are limited to 5 MB, allowed extensions and file signatures are checked, and stored with generated names. The database and uploads live in this project folder. Back up `clothing_resale.db` and `uploads/` together if you need to preserve the demo data.

## Known limitations

- Local demonstration only; no production hosting or HTTPS setup.
- No online payments, delivery tracking, chat, or notifications.
- Seller and buyer arrange collection or delivery themselves.
- SQLite is intended here for a small student project and local testing.
- Google Fonts are an optional visual enhancement; the site falls back to system fonts offline.

## Troubleshooting

- **`No module named flask`:** activate the virtual environment and run `pip install -r requirements.txt`.
- **Port 5000 is busy:** stop the other local app, or change the `app.run()` port at the bottom of `app.py`.
- **Image rejected:** use a real JPG, PNG, or WebP file smaller than 5 MB.
- **Cannot open admin page:** confirm the account's role is `admin` in the SQLite `users` table, then log out and back in.
- **Reset local demo data:** stop the server and remove `clothing_resale.db`; the app creates an empty database on the next start. Uploaded image files can be removed separately from `uploads/`.
