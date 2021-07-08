import os

import json

from sqlalchemy import create_engine

from flask import Flask, session, render_template, request, jsonify

from flask_session import Session

from sqlalchemy.orm import scoped_session, sessionmaker

from classes import User, Book

import requests

app = Flask(__name__)

# Check for DATABASE_URL
if not os.getenv("DATABASE_URL"):
  raise RuntimeError("You need to set DATABASE_URL value")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if "user" not in session.keys() or session["user"] is None:
        return render_template("login.html")
    else:
        return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        result = db.execute("SELECT id, name, email, username, password FROM users WHERE username=:username AND password=:password", {"username": username, "password": password}).fetchone()
        if result is None:
        	return render_template("error.html", message="Username and password do not match")
        else:
            user = User(result.id, result.name, result.email, result.username, result.password)
            
        
            if user:
                session["user"] = user
                return render_template("index.html")
    
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        username = request.form.get("username")
        if not name or not email or not password or not username:
            return render_template("error.html", message="All fields must be inserted")
        else:
            db.execute("INSERT INTO users(name, email, username, password) VALUES (:name, :email, :username, :password)", {"name": name, "email": email, "username": username, "password": password})
            db.commit()
        return render_template("login.html")


@app.route("/layout")
def layout():
    return render_template("layout.html")


@app.route("/logout")
def logout():
    #Clear session
    session["user"] = None
    return render_template("login.html")



@app.route("/books", methods=["GET", "POST"])
def books():
    if session["user"] is None:
        return login()

    # If  GET method render search page
    if request.method == "GET":
        return render_template("books.html")
    else:
         # If POST method perform the seatche with the text provided
        text = "%"+request.form.get("search-text")+"%"
        books = db.execute("SELECT * FROM books WHERE (isbn LIKE :isbn OR title LIKE :title OR author LIKE :author OR year LIKE :year)", {"isbn":text, "title":text, "author":text, "year":text}).fetchall()
        return render_template("books.html", books=books)


@app.route("/details/<string:isbn>", methods=["GET"])
def details(isbn):
    if session["user"] is None:
        return login()
    # retive and return the book details
    book = Book()

    book.isbn, book.title, book.author, book.year, book.reviews_n, book.average_rating = db.execute("SELECT isbn, title, author, year, reviews_n, average_rating FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    
    return render_template("details.html", book=book)


@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):
    """ Give all the details about the book"""
    if request.method == "GET":
        res = db.execute("SELECT title, author, year, isbn, reviews_n, average_rating FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
        book = Book()

        if res is None:
            return render_template("error.html", message="404 book not found"), 404
        
        book.title, book.author, book.year, book.isbn, book.reviews_n, book.average_rating = res
        if res.reviews_n==0 or res.average_rating==0:
            book_aux = api_intern(isbn)
            book.average_rating = book_aux["books"][0]["average_rating"]
            book.reviews_n = book_aux["books"][0]["reviews_n"]

        response = {"title": book.title, "author": book.author, "year": book.year, "isbn": book.isbn, "review_count": book.reviews_n, "average_score": book.average_rating}
        return jsonify(response)
    

def api_intern(isbn):
    #retrive details from online api
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "tG3fNsIrnsgw10HrbsI1Rhdg", "isbns": isbn})

    return res.json()
    

#route to read and post reviews
@app.route("/review/<string:isbn>", methods=["GET", "POST"])
def review(isbn):
    if session["user"] is None:
        return login()

    #if logged in return review submition form
    book = db.execute("SELECT * FROM books WHERE isbn= :isbn"
        , {"isbn": isbn}).fetchone()
    if request.method == "POST":
        review = request.form.get("review")
        score = request.form.get("score")
        #update average
        average_rating = (book.average_rating * book.reviews_n + float(score))/(book.reviews_n + 1)
        reviews_n = book.reviews_n + 1
        comments = db.execute("SELECT * FROM reviews WHERE author_id= :author_id AND book_isbn= :book_isbn", {"author_id": session["user"].id, "book_isbn": isbn}).fetchone()

        #Check if comment already exist
        if comments:
            return render_template("error.html", message="You already posted a comment to this book")

        db.execute("INSERT INTO reviews(review, score, author_id, book_isbn) VALUES (:review, :score, :author_id, :book_isbn)", {"review": review, "score": score, "author_id": session["user"].id, "book_isbn": isbn})
        db.execute("UPDATE books SET average_rating = :average_rating, reviews_n = :reviews_n WHERE isbn=:isbn", {"isbn": isbn, "average_rating": average_rating, "reviews_n": reviews_n})

        db.commit()

    reviews = db.execute("SELECT * FROM reviews WHERE book_isbn= :isbn"
        , {"isbn": isbn}).fetchall()
    return render_template("review.html", book=book, reviews=reviews)