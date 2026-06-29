from flask import Flask, render_template, request, redirect, session, jsonify
import json
import os
from datetime import date
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "static/images"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = "storekey"

FILE = "products.json"
SALES_FILE = "sales.json"


def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default



# -------------------------------
# Product Functions
# -------------------------------

def load_products():
    if not os.path.exists(FILE):
        return []

    with open(FILE, "r") as f:
        return json.load(f)


def save_products(data):
    with open(FILE, "w") as f:
        json.dump(data, f)


# -------------------------------
# Sales Functions
# -------------------------------

def load_sales():
    if not os.path.exists(SALES_FILE):
        return []

    with open(SALES_FILE, "r") as f:
        return json.load(f)


def save_sales(data):
    with open(SALES_FILE, "w") as f:
        json.dump(data, f)


# -------------------------------
# Login
# -------------------------------

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin1":
            session["user"] = username
            return redirect("/dashboard")

    return render_template("login.html")


# -------------------------------
# Dashboard
# -------------------------------

@app.route("/dashboard")
def dashboard():

    products = load_products()

    total_products = len(products)
    total_quantity = sum(safe_int(p.get("quantity")) for p in products)
    total_value = sum(safe_int(p.get("quantity")) * safe_float(p.get("price")) for p in products)

    names = [p.get("name", "") for p in products]
    qty = [safe_int(p.get("quantity")) for p in products]

    # Low stock detection
    low_stock = [p for p in products if safe_int(p.get("quantity")) < 10]

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_quantity=total_quantity,
        total_value=total_value,
        names=names,
        qty=qty,
        products=products,
        low_stock=low_stock
    )


# -------------------------------
# Add Product
# -------------------------------

@app.route("/add")
def add():
    return render_template("add_product.html")


@app.route("/insert", methods=["POST"])
def insert():

    products = load_products()

    name = request.form["name"]
    price = request.form["price"]
    quantity = request.form["quantity"]

    image = request.files["image"]
    filename = ""

    if image and image.filename != "":
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    products.append({
        "name": name,
        "price": price,
        "quantity": quantity,
        "image": filename
    })

    save_products(products)

    return redirect("/view")


# -------------------------------
# View Products
# -------------------------------

@app.route("/view")
def view():

    products = load_products()

    return render_template("view_products.html", products=products)


# -------------------------------
# Delete Product
# -------------------------------

@app.route("/delete/<int:id>")
def delete(id):

    products = load_products()

    if 0 <= id < len(products):
        products.pop(id)
        save_products(products)

    return redirect("/view")


# -------------------------------
# Edit Product
# -------------------------------

@app.route("/edit/<int:id>")
def edit(id):

    products = load_products()

    if id < 0 or id >= len(products):
        return redirect("/view")

    return render_template(
        "edit_product.html",
        product=products[id],
        id=id
    )


@app.route("/update/<int:id>", methods=["POST"])
def update(id):

    products = load_products()

    if 0 <= id < len(products):
        products[id]["name"] = request.form["name"]
        products[id]["price"] = request.form["price"]
        products[id]["quantity"] = request.form["quantity"]
        save_products(products)

    return redirect("/view")


# -------------------------------
# Billing Page
# -------------------------------

@app.route("/billing")
def billing():

    products = load_products()

    return render_template(
        "billing.html",
        products=products
    )


# -------------------------------
# Checkout (Multi Product POS)
# -------------------------------



# -------------------------------
# Daily Sales Report
# -------------------------------

@app.route("/report")
def report():

    sales = load_sales()

    today = str(date.today())

    today_sales = [s for s in sales if s.get("date") == today]

    total_sales = sum(safe_float(s.get("total")) for s in today_sales)

    total_orders = len(today_sales)

    return render_template(
        "report.html",
        sales=today_sales,
        total_sales=total_sales,
        total_orders=total_orders
    )


# -------------------------------
# Complete Sale (POS Checkout)
# -------------------------------

@app.route("/complete-sale", methods=["POST"])
def complete_sale():

    cart = request.get_json()
    if not cart:
        return jsonify({"status": "error", "message": "Cart is empty"}), 400

    sales = load_sales()
    products = load_products()

    for item in cart:
        price = safe_float(item.get("price"))
        qty = safe_int(item.get("qty"))
        
        # Log sale
        sales.append({
            "product": item.get("name", "Unknown"),
            "price": price,
            "quantity": qty,
            "total": price * qty,
            "date": str(date.today())
        })

        # Deduct stock
        for p in products:
            if p.get("name") == item.get("name"):
                current_stock = safe_int(p.get("quantity"))
                p["quantity"] = str(max(0, current_stock - qty))
                break

    save_sales(sales)
    save_products(products)

    return jsonify({"status": "success"})

# -------------------------------
# Run Server
# -------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
