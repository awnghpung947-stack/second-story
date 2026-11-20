# Second Story — Clothing Resale Platform

A beginner-friendly local marketplace where members can list pre-loved clothing, browse available items, and send purchase requests to sellers. One registered account can act as both buyer and seller.

A sanitized demo database is included in `demo/`, so a fresh clone starts with sample listings and accounts. The live `clothing_resale.db` and real user uploads are never committed.

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
demo/                   Sanitized demo database used for a fresh clone
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

Open **http://127.0.0.1:5000/** in your browser. Stop the local server with Ctrl+C. On first start, the app copies `demo/second_story_demo.db` to `clothing_resale.db`, so the site opens with demo listings and accounts.

## Demo accounts

All demo accounts use the password **`demo1234`**.

| Role | Email | Phone |
| --- | --- | --- |
| Seller | `demo.seller@secondstory.test` | 9000000001 |
| Buyer | `demo.buyer@secondstory.test` | 9000000002 |
| Admin | `demo.admin@secondstory.test` | 9000000003 |

The demo data includes pending and accepted purchase requests. Log in as the seller to see the pending-request badge, accept it, then log in as the buyer to see the seller's phone number revealed.

## First use

1. Choose **Join us** and create a regular account, or log in with a demo account above.
2. Log in and choose **Sell an item** to add a clothing listing and photo (JPG, PNG, or WebP, at most 5 MB).
3. Register a second account in a private browser window or after logging out; browse and request the listed item.
4. Log back in as the seller, open **Seller requests**, then accept or reject the pending request. Accepting the request marks the item sold and reveals your mobile number to that buyer on their **My requests** page and the item page.

The app does not collect payments or arrange delivery. Buyer and seller coordinate the handover directly.

## Administrator access

The bundled demo includes an admin account (`demo.admin@secondstory.test`, password `demo1234`), so the admin dashboard is available immediately. Real accounts are not admins by default.

To promote a real account, stop the Flask server, then open `clothing_resale.db` with a SQLite viewer such as DB Browser for SQLite. In the `users` table, change that account's `role` value from `user` to `admin`, save, and restart the app. Never change roles through public forms.

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
- **Reset local demo data:** stop the server and remove `clothing_resale.db`; the bundled demo data is restored on the next start. For a completely empty database, also remove `demo/second_story_demo.db`. Uploaded image files can be removed separately from `uploads/`.
