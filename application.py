import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

post_num = 0

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///avo.db")

@app.route("/")
@login_required
def index():
    return apology("WELCOME TO AVO")

@app.route("/feed", methods=["GET", "POST"])
@login_required
def feed():
    if request.method == "GET":
        rows = db.execute("SELECT * FROM posts ORDER BY id DESC")
        return render_template("feed.html", rows=rows)
    else:
        id = request.form.get("part")
        if not id:
            return apology("Didn't type in post number", 400)
        global post_num
        post_num = id
        return redirect("/single")

@app.route("/single", methods=["GET", "POST"])
@login_required
def single():
    global post_num
    rows = db.execute("SELECT * FROM posts WHERE id=:id", id=post_num)
    if request.method == "GET":
        voted = False
        vote = db.execute("SELECT * FROM votes WHERE post_id=:post_id AND voter_id=:voter_id", post_id=post_num, voter_id=session["user_id"])

        if len(vote) == 0:
            return render_template("single.html", rows=rows, voted=voted)
        else:
            if vote[0]["option1"] == 1:
                option = "option 1"
            elif vote[0]["option2"] == 1:
                option = "option 2"
            if vote[0]["option3"] == 1:
                option = "option 3"
            voted = True
            return render_template("single.html", rows=rows, voted=voted, option=option)

    else:
        vote = request.form.get("vote")
        if vote == "1":
            new_total = rows[0]["option1_count"] + 1
            db.execute("UPDATE posts SET option1_count = :new_total WHERE id = :id", new_total = new_total, id = post_num)
            db.execute("INSERT INTO votes (post_id, voter_id, option1) VALUES (:post_id, :voter_id, :option1)", post_id = post_num, voter_id=session["user_id"], option1=1)
        if vote == "2":
            new_total = rows[0]["option2_count"] + 1
            db.execute("UPDATE posts SET option2_count = :new_total WHERE id = :id", new_total = new_total, id = post_num)
            db.execute("INSERT INTO votes (post_id, voter_id, option2) VALUES (:post_id, :voter_id, :option2)", post_id = post_num, voter_id=session["user_id"], option2=1)
        if vote == "3":
            new_total = rows[0]["option2_count"] + 1
            db.execute("UPDATE posts SET option3_count = :new_total WHERE id = :id", new_total = new_total, id = post_num)
            db.execute("INSERT INTO votes (post_id, voter_id, option3) VALUES (:post_id, :voter_id, :option3)", post_id = post_num, voter_id=session["user_id"], option3=1)

        return redirect("/single")

@app.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "GET":
        return render_template("new.html")
    else:
        textdata = request.form.get("editordata")
        if not textdata or textdata == "Explain your circumstance or conflict":
            return apology("Missing post", 400)

        first_opt = request.form.get("first_opt")
        second_opt = request.form.get("second_opt")
        third_opt = request.form.get("third_opt")
        num_opt = 0
        if first_opt:
            num_opt += 1
        if second_opt:
            num_opt += 1
        if third_opt:
            num_opt += 1
        if not num_opt >= 2:
            return apology("Gotta give at least two options", 400)

        db.execute("INSERT INTO posts (user_id, text, option1, option2, option3) VALUES (:user_id, :text, :option1, :option2, :option3)", user_id=session["user_id"], text=textdata, option1=first_opt, option2=second_opt, option3=third_opt)
        return redirect("/feed")


@app.route("/mypost", methods=["GET", "POST"])
@login_required
def mypost():
    if request.method == "GET":
        rows = db.execute("SELECT * FROM posts WHERE user_id=:user_id ORDER BY id DESC", user_id=session["user_id"])
        return render_template("mypost.html", rows=rows)


@app.route("/myvote", methods=["GET", "POST"])
@login_required
def myvote():
    if request.method == "GET":
        rows = db.execute("SELECT * FROM posts JOIN votes ON posts.id=votes.post_id WHERE voter_id=:voter_id", voter_id=session["user_id"])
        return render_template("myvote.html", rows=rows)
    else:
        id = request.form.get("part")
        all_id = db.execute("SELECT id FROM posts")
        print(all_id)
        if not id:
            return apology("Didn't type in post number", 400)
        global post_num
        post_num = id
        return redirect("/single")



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/feed")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/feed")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        if not username:
            return apology("Invalid username", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=username)

        # Ensure username exists and password is correct
        if len(rows) == 1:
            return apology("invalid username", 403)

        password = request.form.get("password")
        if not password:
            return apology("Missing Password", 400)

        confirmation = request.form.get("confirmation")
        if not confirmation or password != confirmation:
            return apology("passwords don't match", 400)

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=generate_password_hash(password))
        return redirect("/feed")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
