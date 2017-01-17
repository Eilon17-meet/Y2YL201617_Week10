from flask import *
from model import *
from flask import session as login_session
import string
import locale

app = Flask(__name__)
app.secret_key = "MY_SUPER_SECRET_KEY"


engine = create_engine('sqlite:///fizzBuzz.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine, autoflush=False)
session = DBSession()

admin_email='eilon246810@gmail.com'

def verify_password(email,password):
	customer= session.query(Customer).filter_by(email= email).first()
	if not customer or not customer.verify_password(password):
		return False
	g.customer= customer
	return True

def calculateTotal(shoppingCart):
	total=0.0
	locale.setlocale( locale.LC_ALL, '' )
	for item in shoppingCart.products:
		total+=item.quantity*float(item.product.price[1:])
	return total

def generateConfirmationNumber():
	return ''.join(random.choice(string.ascii_uppercase+string.digits) for x in xrange(16))

@app.route('/')
def index():
	return redirect(url_for('inventory'))

@app.route('/hello/')
@app.route("/hello/<name>")
def hello(name=None):
	return render_template('hello_page.html',name=name)

@app.route('/inventory')
def inventory():
	items = session.query(Product).all()
	return render_template("inventory.html",items=items)

@app.route('/user/<username>')
def show_user_profile(username):
	# show the user profile for that user
	return 'User %s' % username

@app.route('/post/<int:post_id>')
def show_post(post_id):
	# show the post with the given id, the id is an integer
	return 'Post %d' % post_id


@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'GET':
		return render_template("login.html")
	elif request.method == 'POST':
		email = request.form['email']
		password = request.form['password']
		if email is None or password is None:
			flash('missing somthing...')
			return redirect(url_for('login'))
		if verify_password(email,password):
			customer = session.query(Customer).filter_by(email=email).one()
			
			
			login_session['name'] = customer.name
			login_session['email'] = customer.email
			login_session['id'] = customer.id
			if email==admin_email:
				return redirect(url_for('admin_page'))

			flash ('login Successful! Welcome, agent 00-%s' % customer.name)
			return redirect(url_for('inventory'))
		else:
			flash('Incorrect username/password combination')
			return redirect(url_for('login'))

@app.route('/newCustomer', methods = ['GET','POST'])
def newCustomer():
	if request.method == 'POST':
		name = request.form['name']
		email = request.form['email']
		password = request.form['password']
		address = request.form['address']
		if name is None or email is None or password is None:
			flash("Your form is missing arguments")
			return redirect(url_for('newCustomer'))
		if session.query(Customer).filter_by(email = email).first() is not None or email==admin_email:
			flash("A user with this email address already exists")
			return redirect(url_for('newCustomer'))
		customer = Customer(name = name, email=email, address = address)
		customer.hash_password(password)
		session.add(customer)
		shoppingCart = ShoppingCart(customer=customer)
		session.add(shoppingCart)
		session.commit()
		flash("User Created Successfully!")
		return redirect(url_for('inventory'))
	else:
		return render_template('newCustomer.html')


@app.route("/product/<int:product_id>")
def product(product_id):
	product= session.query(Product).filter_by(id= product_id).one()
	return render_template('product.html',product=product)

@app.route("/product/<int:product_id>/addToCart", methods = ['POST'])
def addToCart(product_id):
	if 'id' not in login_session:
		flash("You must be logged in to perform this action, 007")
		return redirect(url_for('login'))
	quantity = request.form['quantity']
	product = session.query(Product).filter_by(id = product_id).one()
	shoppingCart = session.query(ShoppingCart).filter_by(customer_id = login_session['id']).one()
	if product.name in [item.product.name for item in shoppingCart.products]:
		assoc = session.query(ShoppingCartAssociation).filter_by(shoppingCart= shoppingCart) \
			.filter_by(product= product).one()
		assoc.quantity = int(assoc.quantity) + int(quantity)
		flash("Successfuly added to Shopping Cart")
		return redirect(url_for('shoppingCart'))
	else:
		a = ShoppingCartAssociation(product= product, quantity=quantity)
		shoppingCart.products.append(a)
		session.add_all([a,product,shoppingCart])
		session.commit()
		flash("Successfuly added to Shopping Cart")
		return redirect(url_for('shoppingCart'))
		

@app.route("/shoppingCart")
def shoppingCart():
	if 'id' not in login_session:
		flash("You must be logged in to perform this action, 007")
		return redirect(url_for('login'))
	shoppingCart=session.query(ShoppingCart).filter_by(customer_id=login_session['id']).one()
	return render_template('shoppingCart.html', shoppingCart=shoppingCart)

@app.route("/removeFromCart/<int:product_id>", methods = ['POST'])
def removeFromCart(product_id):
	if 'id' not in login_session:
		flash("You must be logged in to perform this action, 007")
		return redirect(url_for('login'))
	shoppingCart=session.query(ShoppingCart).filter_by(customer_id=login_session['id']).one()
	association=session.query(ShoppingCartAssociation).filter_by(shoppingCart=shoppingCart).filter_by(product_id=product_id).one()
	session.delete(association)
	session.commit()
	flash("Item extarminated successfully.")
	return redirect(url_for('shoppingCart'))

@app.route("/updateQuantity/<int:product_id>", methods = ['POST'])
def updateQuantity(product_id):
	if 'id' not in login_session:
		flash("You must be logged in to perform this action, 007")
		return redirect(url_for('login'))
	quantity=request.form['quantity']
	if quantity==0:
		return removeFromCart(product_id)
	shoppingCart=session.query(ShoppingCart).filter_by(customer_id=login_session['id']).one()
	assoc=session.query(ShoppingCartAssociation).filter_by(shoppingCart=shoppingCart).filter_by(product_id=product_id).one()
	assoc.quantity=quantity
	session.add(assoc)
	session.commit()
	flash("Quantity Updated Succsessfully.")
	return redirect(url_for('shoppingCart'))

@app.route("/checkout", methods = ['GET', 'POST'])
def checkout():
	if 'id' not in login_session:
		flash("You must be logged in to perform this action, 007")
		return redirect(url_for('login'))
	shoppingCart=session.query(ShoppingCart).filter_by(customer_id=login_session['id']).one()
	if request.method=='POST':
		order=Order(customer_id=login_session['id'],confirmation=generateConfirmationNumber())
		order.total=calculateTotal(shoppingCart)
		for item in shoppingCart.products:
			assoc=OrdersAssociation(product=item.product,product_qty=item.quantity)
			order.products.append(assoc)
			session.delete(item)
		session.add_all([order,shoppingCart])
		session.commit()
		return redirect(url_for('confirmation', confirmation=order.confirmation))
	elif request.method=='GET':
		return render_template('checkout.html',shoppingCart=shoppingCart,total=calculateTotal(shoppingCart))

@app.route("/confirmation/<confirmation>")
def confirmation(confirmation):
	if 'name' not in login_session:
		flash("You must be logged in to perform this action, 007")
		return redirect(url_for('login'))
	order=session.query(Order).filter_by(confirmation=confirmation).one()
	return render_template('confirmation.html', order=order)

@app.route('/logout/are_you_sure', methods = ['GET', 'POST'])
def are_you_sure_to_log_out():
	if 'name' not in login_session:
		flash("You must be logged in order to log out, 007")
		return redirect(url_for('login'))
	if request.method=='GET':
		return render_template('are_you_sure.html')
	elif request.method=='POST':
		if request.form['choice']=='yes':
			return redirect(url_for('logout'))
		else:
			return redirect(url_for('inventory'))

@app.route('/logout/are_you_sure/<choice>')

@app.route('/logout')
def logout():
	if are_you_sure_to_log_out():
		del login_session['name']
		del login_session['email']
		del login_session['id']
		flash("Logged Out Succefully. May The Force Be With You, Agent")
		return redirect(url_for('inventory'))

if __name__ == '__main__':
	app.run(debug=True)
