from flask import Flask, render_template, request, session, redirect, url_for
import pyrebase
import numpy as np
import pickle
import pandas as pd
import json
import firebase_admin
from firebase_admin import db, credentials


app = Flask(__name__, static_folder='images')

# Load the model and dataset
pipe = pickle.load(open('./pipe.pkl', 'rb'))
dataset = pickle.load(open('./dataset.pkl', 'rb'))
laptops = pickle.load(open('./laptopList.pkl', 'rb'))

#assign firebase configuration
config = {
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()
auth = firebase.auth()

app.secret_key = 'secretKey'

# Routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            auth.create_user_with_email_and_password(email, password)
            user = auth.sign_in_with_email_and_password(email, password)
            session['logged_in'] = True
            session['idToken'] = user['idToken']
            session['email'] = user['email']
            return redirect(url_for('home'))
        except:
            return render_template('signup.html', error="Error creating account. Try again.")
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['logged_in'] = True
            session['idToken'] = user['idToken']
            session['email'] = user['email']
            return redirect(url_for('home'))
        except:
            return render_template('login.html', error="Invalid credentials. Try again.")
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('signup'))

@app.route('/')
def home():
    if 'logged_in' in session:
        return render_template('index.html', dataset=dataset, ramList=[2, 4, 8, 16, 24, 32, 64], flag=['Yes', 'No'], resolution_options=['1920x1080', '1366x768', '1600x900', '3840x2160', '3200x1800', '2880x1800', '2560x1600', '2560x1440', '2304x1440'], memorySizeList=[0, 128, 256, 512, 1024])
    else:
        return redirect(url_for('signup'))

@app.route('/overview')
def overview():
    return render_template('overview.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        brand = request.form['brand']
        type = request.form['type']
        ram = int(request.form['ram'])
        weight = float(request.form['weight'])
        touchScreen = 1 if request.form['touchScreen'] == 'Yes' else 0
        ips = 1 if request.form['ips'] == 'Yes' else 0
        screenSize = float(request.form['screenSize'])
        resolution = request.form['resolution']
        cpu = request.form['cpu']
        hdd = int(request.form['hdd'])
        ssd = int(request.form['ssd'])
        gpu = request.form['gpu']
        os = request.form['os']

        X_res = int(resolution.split('x')[0])
        Y_res = int(resolution.split('x')[1])
        ppi = (((X_res**2) + (Y_res**2))**0.5) / screenSize
        
        # Ensure all inputs are in the correct format
        query = np.array([brand, type, ram, weight, touchScreen, ips, ppi, cpu, hdd, ssd, gpu, os], dtype=object)

        # Reshape query for prediction
        query = query.reshape(1, 12)

        # Print query for debugging
        print("Query:", query)

        # Predict and convert the output to a readable format
        prediction = int(np.exp(pipe.predict(query)[0]))
        # Prepare the parameters to send to the result page

        params = {
            'UserID':session['idToken'],
            'Username':session['email'],
            'Brand': brand,
            'Type': type,
            'RAM (in GB)': ram,
            'Weight': weight,
            'Touchscreen': 'Yes' if touchScreen == 1 else 'No',
            'IPS': 'Yes' if ips == 1 else 'No',
            'Screen Size': screenSize,
            'Resolution': resolution,
            'CPU': cpu,
            'HDD (in GB)': hdd,
            'SSD (in GB)': ssd,
            'GPU': gpu,
            'Operating System': os,
            'Predicted Price (in ₹)': prediction
        }
        result = db.child("Result").get()
        print(result)
        return render_template('result.html', params=params)
    
    except Exception as e:
        # Print the exception for debugging
        print("Error during prediction:", e)
        return render_template('index.html', dataset=dataset, ramList=[2, 4, 8, 16, 24, 32, 64], flag=['Yes', 'No'], resolution_options=['1920x1080', '1366x768', '1600x900', '3840x2160', '3200x1800', '2880x1800', '2560x1600', '2560x1440', '2304x1440'], memorySizeList=[0, 128, 256, 512, 1024], error=str(e))

@app.route('/checkout')
def checkout():
    try:
        brand = request.args.get('brand', 'Apple').capitalize()
        return render_template('checkout.html', laptops=laptops, brand=brand)
    
    except Exception as e:
        print("Error during checkout:", e)
        return render_template('error.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True)
