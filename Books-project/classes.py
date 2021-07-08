class User:
	def __init__(self, id=0, name="", email="", username="", password=""):
		self.id = id
		self.name = name
		self.email = email
		self.username = username
		self.password = password

class Book:
	def __init__(self, id=0, isbn="", title="", author="", year="", reviews_n=0, average_rating=0.0):
		self.id = id
		self.isbn = isbn
		self.title = title
		self.author = author
		self.year = year
		self.reviews_n = reviews_n
		self.average_rating = average_rating