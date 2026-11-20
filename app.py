"""A small Flask clothing resale marketplace for local demonstration."""
import os
import re
import secrets
import shutil
import sqlite3
import uuid
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
SEED_DATABASE = ROOT / "demo" / "second_story_demo.db"
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "change-this-local-development-key"),
    DATABASE=str(ROOT / "clothing_resale.db"),
    UPLOAD_FOLDER=str(ROOT / "uploads"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)
ALLOWED = {"jpg", "jpeg", "png", "webp"}
CATEGORIES = ["T-shirts", "Shirts", "Hoodies and sweatshirts", "Jackets",
              "Jeans and trousers", "Shorts", "Shoes", "Other clothing"]
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "Other"]
CONDITIONS = ["New with tags", "Like new", "Good", "Fair"]

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
 phone TEXT NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user'
 CHECK(role IN ('user','admin')), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS clothing (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 name TEXT NOT NULL, category TEXT NOT NULL, brand TEXT NOT NULL, size TEXT NOT NULL,
 condition TEXT NOT NULL, price REAL NOT NULL CHECK(price >= 0), description TEXT NOT NULL,
 image TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'available'
 CHECK(status IN ('available','sold')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS purchase_requests (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 buyer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 clothing_id INTEGER NOT NULL REFERENCES clothing(id) ON DELETE CASCADE,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected')),
 request_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS clothing_status_date ON clothing(status, created_at);
CREATE INDEX IF NOT EXISTS requests_seller ON purchase_requests(seller_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS one_pending_request ON purchase_requests(buyer_id, clothing_id) WHERE status='pending';
"""

def connect_db():
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    with connect_db() as db:
        db.executescript(SCHEMA)

def prepare_database():
    """Create the local database, seeding it with demo data on a fresh clone."""
    db_path = Path(app.config["DATABASE"])
    if not db_path.exists() and SEED_DATABASE.exists():
        shutil.copyfile(SEED_DATABASE, db_path)
    init_db()

@app.before_request
def before_request():
    g.db = connect_db()
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)

@app.teardown_request
def teardown_request(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.context_processor
def inject_globals():
    user = current_user()
    pending_requests = 0
    if user:
        pending_requests = g.db.execute(
            "SELECT COUNT(*) FROM purchase_requests WHERE seller_id=? AND status='pending'",
            (user["id"],)).fetchone()[0]
    return {"current_user": user, "csrf_token": session.get("csrf_token"),
            "categories": CATEGORIES, "sizes": SIZES, "conditions": CONDITIONS,
            "pending_seller_requests": pending_requests}

def current_user():
    user_id = session.get("user_id")
    return g.db.execute("SELECT id,name,email,phone,role,created_at FROM users WHERE id=?", (user_id,)).fetchone() if user_id else None

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user()["role"] != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

@app.before_request
def verify_csrf():
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        if not sent or not secrets.compare_digest(sent, session.get("csrf_token", "")):
            abort(400, "The form expired. Please go back, refresh, and try again.")

def save_image(file):
    if not file or not file.filename:
        return None
    safe = secure_filename(file.filename)
    ext = safe.rsplit(".", 1)[-1].lower() if "." in safe else ""
    if ext not in ALLOWED:
        raise ValueError("Choose a JPG, PNG, or WebP image.")
    # Verify file signatures rather than relying only on the submitted MIME type.
    data = file.stream.read(16)
    file.stream.seek(0)
    valid = (data.startswith(b"\xff\xd8\xff") if ext in {"jpg", "jpeg"} else
             data.startswith(b"\x89PNG\r\n\x1a\n") if ext == "png" else
             len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP")
    if not valid:
        raise ValueError("The image file does not match its extension.")
    name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], name))
    return name

def delete_image(name):
    if name:
        path = os.path.join(app.config["UPLOAD_FOLDER"], os.path.basename(name))
        if os.path.isfile(path):
            os.remove(path)

def item_form_values():
    return {key: request.form.get(key, "").strip() for key in
            ("name", "category", "brand", "size", "condition", "price", "description")}

def validate_item(values):
    if any(not values[k] for k in values):
        return "Please complete every field."
    if values["category"] not in CATEGORIES or values["size"] not in SIZES or values["condition"] not in CONDITIONS:
        return "Choose a valid category, size, and condition."
    try:
        price = float(values["price"])
        if price < 0 or price > 10000000:
            raise ValueError()
    except ValueError:
        return "Enter a valid price between ₹0 and ₹10,000,000."
    if len(values["name"]) > 100 or len(values["description"]) > 2000:
        return "The item name or description is too long."
    return None

@app.route("/")
def index():
    items = g.db.execute("SELECT c.*,u.name seller_name FROM clothing c JOIN users u ON u.id=c.seller_id WHERE c.status='available' ORDER BY c.created_at DESC LIMIT 8").fetchall()
    return render_template("index.html", items=items)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email, phone = (request.form.get(k, "").strip() for k in ("name", "email", "phone"))
        password, confirm = request.form.get("password", ""), request.form.get("confirm", "")
        error = ("Please complete every field." if not all((name,email,phone,password,confirm)) else
                 "Enter a valid email address." if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) else
                 "Use a password with at least 8 characters." if len(password) < 8 else
                 "The passwords do not match." if password != confirm else None)
        if error:
            flash(error, "error")
        else:
            try:
                cur = g.db.execute("INSERT INTO users(name,email,phone,password) VALUES(?,?,?,?)", (name,email.lower(),phone,generate_password_hash(password)))
                g.db.commit()
                session.clear(); session["user_id"] = cur.lastrowid; session["csrf_token"] = secrets.token_urlsafe(32)
                flash("Your account is ready. Welcome!", "success")
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                flash("That email address is already registered.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email, password = request.form.get("email", "").strip().lower(), request.form.get("password", "")
        user = g.db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear(); session["user_id"] = user["id"]; session["csrf_token"] = secrets.token_urlsafe(32)
            flash("You are now logged in.", "success")
            target = request.args.get("next", "")
            return redirect(target if target.startswith("/") and not target.startswith("//") else url_for("index"))
        flash("Email or password was incorrect.", "error")
    return render_template("login.html")

@app.post("/logout")
def logout():
    session.clear(); flash("You have logged out.", "success")
    return redirect(url_for("index"))

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

@app.route("/browse")
def browse():
    q, category, size = (request.args.get(k, "").strip() for k in ("q", "category", "size"))
    where, args = ["c.status='available'"], []
    if q:
        where.append("(c.name LIKE ? OR c.brand LIKE ?)"); args.extend([f"%{q}%", f"%{q}%"])
    if category in CATEGORIES:
        where.append("c.category=?"); args.append(category)
    if size in SIZES:
        where.append("c.size=?"); args.append(size)
    for key, op in (("min_price", ">="), ("max_price", "<=")):
        val = request.args.get(key, "").strip()
        if val:
            try:
                number = float(val)
                if number < 0: raise ValueError()
                where.append(f"c.price {op} ?"); args.append(number)
            except ValueError:
                flash("Price filters must be non-negative numbers.", "error")
    items = g.db.execute("SELECT c.*,u.name seller_name FROM clothing c JOIN users u ON u.id=c.seller_id WHERE " + " AND ".join(where) + " ORDER BY c.created_at DESC", args).fetchall()
    return render_template("browse.html", items=items)

@app.route("/item/<int:item_id>")
def details(item_id):
    item = g.db.execute("SELECT c.*,u.name seller_name FROM clothing c JOIN users u ON u.id=c.seller_id WHERE c.id=?", (item_id,)).fetchone()
    if not item: abort(404)
    # A seller's phone number is private until that seller accepts this buyer's request.
    my_request, revealed_phone = None, None
    if current_user():
        my_request = g.db.execute(
            "SELECT * FROM purchase_requests WHERE buyer_id=? AND clothing_id=? "
            "ORDER BY CASE status WHEN 'accepted' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, request_date DESC LIMIT 1",
            (current_user()["id"], item_id)).fetchone()
        if my_request and my_request["status"] == "accepted":
            revealed_phone = g.db.execute("SELECT phone FROM users WHERE id=?", (item["seller_id"],)).fetchone()["phone"]
    return render_template("details.html", item=item, my_request=my_request, revealed_phone=revealed_phone)

@app.route("/sell", methods=["GET", "POST"])
@login_required
def add_clothing():
    values = item_form_values()
    if request.method == "POST":
        error = validate_item(values)
        image = None
        try:
            if not error:
                image = save_image(request.files.get("image"))
                if not image: error = "Please choose a clothing photograph."
        except ValueError as exc:
            error = str(exc)
        if error: flash(error, "error")
        else:
            g.db.execute("INSERT INTO clothing(seller_id,name,category,brand,size,condition,price,description,image) VALUES(?,?,?,?,?,?,?,?,?)",
                         (current_user()["id"], values["name"],values["category"],values["brand"],values["size"],values["condition"],float(values["price"]),values["description"],image))
            g.db.commit(); flash("Your item is listed.", "success"); return redirect(url_for("my_listings"))
    return render_template("item_form.html", item=None, values=values)

@app.route("/my-listings")
@login_required
def my_listings():
    items = g.db.execute("SELECT * FROM clothing WHERE seller_id=? ORDER BY created_at DESC", (current_user()["id"],)).fetchall()
    return render_template("my_listings.html", items=items)

@app.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_clothing(item_id):
    item = g.db.execute("SELECT * FROM clothing WHERE id=? AND seller_id=?", (item_id,current_user()["id"])).fetchone()
    if not item: abort(404)
    values = item_form_values() if request.method == "POST" else dict(item)
    if request.method == "POST":
        error = validate_item(values); image = item["image"]
        try:
            new_image = save_image(request.files.get("image"))
            if new_image: image = new_image
        except ValueError as exc: error = str(exc)
        if error: flash(error,"error")
        else:
            g.db.execute("UPDATE clothing SET name=?,category=?,brand=?,size=?,condition=?,price=?,description=?,image=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND seller_id=?",
                (values["name"],values["category"],values["brand"],values["size"],values["condition"],float(values["price"]),values["description"],image,item_id,current_user()["id"]))
            g.db.commit()
            if image != item["image"]: delete_image(item["image"])
            flash("Listing updated.","success"); return redirect(url_for("my_listings"))
    return render_template("item_form.html", item=item, values=values)

@app.post("/item/<int:item_id>/delete")
@login_required
def delete_clothing(item_id):
    item = g.db.execute("SELECT * FROM clothing WHERE id=? AND seller_id=?", (item_id,current_user()["id"])).fetchone()
    if not item: abort(404)
    g.db.execute("DELETE FROM clothing WHERE id=?", (item_id,)); g.db.commit(); delete_image(item["image"])
    flash("Listing deleted.","success"); return redirect(url_for("my_listings"))

@app.post("/item/<int:item_id>/request")
@login_required
def request_to_buy(item_id):
    buyer_id = current_user()["id"]
    try:
        # BEGIN IMMEDIATE serializes competing state changes in SQLite.
        g.db.execute("BEGIN IMMEDIATE")
        item = g.db.execute("SELECT * FROM clothing WHERE id=?", (item_id,)).fetchone()
        if not item or item["status"] != "available" or item["seller_id"] == buyer_id:
            g.db.rollback(); flash("This item is no longer available for your request.","error")
        else:
            g.db.execute("INSERT INTO purchase_requests(buyer_id,seller_id,clothing_id) VALUES(?,?,?)", (buyer_id,item["seller_id"],item_id))
            g.db.commit(); flash("Request sent. The seller's phone number will appear once they confirm it.","success")
    except sqlite3.IntegrityError:
        g.db.rollback(); flash("You already have a pending request for this item.","error")
    return redirect(url_for("details",item_id=item_id))

@app.route("/my-requests")
@login_required
def my_requests():
    rows = g.db.execute("SELECT r.*,c.name item_name,c.image,c.price,u.name seller_name,u.phone seller_phone FROM purchase_requests r JOIN clothing c ON c.id=r.clothing_id JOIN users u ON u.id=r.seller_id WHERE r.buyer_id=? ORDER BY (r.status='accepted') DESC,r.request_date DESC", (current_user()["id"],)).fetchall()
    return render_template("requests.html", rows=rows, title="My requests", seller_view=False)

@app.route("/seller-requests")
@login_required
def seller_requests():
    rows = g.db.execute("SELECT r.*,c.name item_name,c.image,c.price,u.name buyer_name,u.phone buyer_phone FROM purchase_requests r JOIN clothing c ON c.id=r.clothing_id JOIN users u ON u.id=r.buyer_id WHERE r.seller_id=? ORDER BY (r.status='pending') DESC,r.request_date DESC", (current_user()["id"],)).fetchall()
    pending_count = sum(1 for row in rows if row["status"] == "pending")
    return render_template("requests.html", rows=rows, title="Requests for my listings", seller_view=True,
                           pending_count=pending_count)

@app.post("/request/<int:request_id>/<action>")
@login_required
def decide_request(request_id, action):
    if action not in {"accept", "reject"}: abort(400)
    try:
        g.db.execute("BEGIN IMMEDIATE")
        row = g.db.execute("SELECT r.*,c.status item_status FROM purchase_requests r JOIN clothing c ON c.id=r.clothing_id WHERE r.id=? AND r.seller_id=? AND r.status='pending'", (request_id,current_user()["id"])).fetchone()
        if not row:
            g.db.rollback(); flash("This request has already been processed.","error")
        elif action == "accept" and row["item_status"] != "available":
            g.db.rollback(); flash("This item is not available anymore.","error")
        else:
            status = "accepted" if action == "accept" else "rejected"
            g.db.execute("UPDATE purchase_requests SET status=? WHERE id=?", (status,request_id))
            if status == "accepted":
                g.db.execute("UPDATE clothing SET status='sold',updated_at=CURRENT_TIMESTAMP WHERE id=?",(row["clothing_id"],))
                g.db.execute("UPDATE purchase_requests SET status='rejected' WHERE clothing_id=? AND id<>? AND status='pending'",(row["clothing_id"],request_id))
            g.db.commit()
            flash("Request accepted. The buyer can now see your phone number to arrange the handover." if status == "accepted"
                  else "Request rejected.", "success")
    except sqlite3.Error:
        g.db.rollback(); flash("Could not update that request. Please try again.","error")
    return redirect(url_for("seller_requests"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    counts = {"users":g.db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
              "listings":g.db.execute("SELECT COUNT(*) FROM clothing").fetchone()[0],
              "available":g.db.execute("SELECT COUNT(*) FROM clothing WHERE status='available'").fetchone()[0],
              "sold":g.db.execute("SELECT COUNT(*) FROM clothing WHERE status='sold'").fetchone()[0],
              "requests":g.db.execute("SELECT COUNT(*) FROM purchase_requests").fetchone()[0]}
    return render_template("admin.html", counts=counts,
        users=g.db.execute("SELECT id,name,email,role,created_at FROM users ORDER BY created_at DESC").fetchall(),
        items=g.db.execute("SELECT c.*,u.name seller_name FROM clothing c JOIN users u ON u.id=c.seller_id ORDER BY c.created_at DESC").fetchall())

@app.post("/admin/item/<int:item_id>/delete")
@admin_required
def admin_delete_listing(item_id):
    item = g.db.execute("SELECT image FROM clothing WHERE id=?", (item_id,)).fetchone()
    if item:
        g.db.execute("DELETE FROM clothing WHERE id=?", (item_id,)); g.db.commit(); delete_image(item["image"])
        flash("Listing removed.","success")
    return redirect(url_for("admin_dashboard"))

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="That page or listing could not be found."),404

@app.errorhandler(403)
def forbidden(error):
    return render_template("error.html", code=403, message="You do not have permission to view this page."),403

@app.errorhandler(413)
def too_large(error):
    return render_template("error.html", code=413, message="Images must be smaller than 5 MB."),413

with app.app_context():
    prepare_database()

if __name__ == "__main__":
    app.run(debug=True)
