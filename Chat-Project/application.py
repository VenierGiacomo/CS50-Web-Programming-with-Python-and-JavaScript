import os

import json
from models import *
from flask import Flask, session, render_template, request, session, jsonify
from flask_session import Session
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_


app = Flask(__name__)

database = SQLAlchemy()

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
def index():
    if "user" not in session.keys() or session["user"] is None:
        return render_template("login.html")
    else:
        return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        email = request.form.get("email")
        name = request.form.get("name")
       
        password = request.form.get("password")

        if not email or not name or not password:
            return render_template("error.html", message="Both Username and password must be submited")
        # Create new user
        user = User(name=name, email=email, password=password)

        #Add new user in the database
        user.create_user()

        return render_template("login.html")

@app.route("/logout")
def logout():
    #Clear session
    session["user"] = None
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not email or not password:
            return render_template("error.html", message="Both Username and password must be submited")
        user = User.query.filter_by(email=email).first()
        if user is None or user.password != password:
        	return render_template("error.html", message="Username and password don't match")
        else:
            session["user"] = user
            return render_template("index.html")
    
    return render_template("login.html")


@app.route("/my_channels", methods=["GET"])
def my_channels():
    #return user chanlles
    channels = User_has_channel.query.filter_by(user_id=session["user"].id)
    user_channels = []
    for channel in channels:
        chann = Channel.query.filter_by(id=channel.channel_id).first()
        user_channels.append(chann)

    return render_template("my_channels.html", my_channels=user_channels)


@app.route("/channel/<string:id>", methods=["GET"])
def channel(id):
    if request.method == "GET":
        # Checks if the user is in this channel
        if session['user'] is None:
            return   render_template("login.html")
        user = User_has_channel.query.filter(and_(User_has_channel.user_id == session['user'].id, User_has_channel.channel_id == id)).first()
        channel = Channel.query.get(id)
        if user == None:
            channel.create_user_in_channel(session['user'].id)

        return render_template("messages.html", channel=channel, messages=channel.messages)
    


@app.route("/others_channels", methods=["GET"])
def others_channels():
    if session['user'] is None:
            return   render_template("login.html")
    # check in which channels the user is not present
    channels = User_has_channel.query.filter_by(user_id=session["user"].id)
    user_channels = []
    for channel in channels:
        c = Channel.query.filter_by(id=channel.channel_id).first()
        user_channels.append(c)
    
    others_channels = Channel.query.all()

    
    for channel in user_channels:
        others_channels.remove(channel)
    return render_template("others_channels.html", others_channels=others_channels)

@socketio.on("create channel")
#create live chat channel if not existent
def socket_create_channel(data):
    channel = Channel.query.filter_by(name=data['name']).first()
    if channel == None:
        basic_chan = Channel(name=data['name'], user_id=session['user'].id)
        basic_chan = basic_chan.create_channel()
        basic_chan.create_user()
        data['id'] = basic_chan.id 
        emit("channel created", data, broadcast=True)    
     


@socketio.on("send message")
def socket_send_message(data):
    # Checks if the user is in this channel
    if session['user'] is None:
            return   render_template("login.html")
        
    channel_id = data["channel_id"]
    message = data["message"]
    channel = Channel.query.get(channel_id)
    user_channels = User_has_channel.query.filter_by(user_id=session["user"].id)
    if channel in user_channels:
        channel.create_message(message, session['user'].id)
        data['user_id'] = session['user'].id
        emit("message received", data, broadcast=True)
    else:
        return render_template("error.html", message="You are not part of this channel")


