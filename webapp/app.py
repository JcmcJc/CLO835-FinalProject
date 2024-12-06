from flask import Flask, render_template, request, url_for
from pymysql import connections
import os
import random
import argparse
import boto3
import botocore
app = Flask(__name__)

DBHOST = os.environ.get("DBHOST") or "localhost"
DBUSER = os.environ.get("DBUSER") or "root"
DBPWD = os.environ.get("DBPWD") or "passwors"
DATABASE = os.environ.get("DATABASE") or "employees"
COLOR_FROM_ENV = os.environ.get('APP_COLOR') or "lime"
DBPORT = int(os.environ.get("DBPORT"))

#ENV varaibles to grab image and show my name
BACKGROUND_IMAGE = os.environ.get("BACKGROUND_IMAGE") or "Invalid image"
MY_NAME = os.environ.get('NAME') or "Jonmarc Jackson"

# Create a connection to the MySQL database
db_conn = connections.Connection(
    host= DBHOST,
    port=DBPORT,
    user= DBUSER,
    password= DBPWD,
    db= DATABASE
)
output = {}
table = 'employee';

# Define the supported color codes
color_codes = {
    "red": "#e74c3c",
    "green": "#16a085",
    "blue": "#89CFF0",
    "blue2": "#30336b",
    "pink": "#f4c2c2",
    "darkblue": "#130f40",
    "lime": "#C1FF9C",
}


# Create a string of supported colors
SUPPORTED_COLORS = ",".join(color_codes.keys())

# Generate a random color
COLOR = random.choice(["red", "green", "blue", "blue2", "darkblue", "pink", "lime"])

@app.route("/", methods=['GET', 'POST'])
def home():
    image_url = url_for('static', filename='background.png')
    return render_template('addemp.html', background_image = image_url, my_name = MY_NAME)
    
#Download image from S3 bucket    
@app.route("/download", methods=['GET','POST'])
def download_image(image_url):
   try:
         bucket = image_url.split('//')[1].split('.')[0]
         object_name = '/'.join(image_url.split('//')[1].split('/')[1:])

         s3 = boto3.resource('s3')
         image_dir = "static" #Default directory
         
         if not os.path.exists(image_dir):
                 os.makedirs(image_dir)
         output = os.path.join(image_dir, "background.png")
         s3.Bucket(bucket).download_file(object_name, output)

         return output

   except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == "404":
                    print("This object is not in the bucket.")
                else:
                    raise

@app.route("/about", methods=['GET','POST'])
def about():
    image_url = url_for('static', filename='background.png')
    return render_template('about.html', background_image = image_url, my_name = MY_NAME)
    
@app.route("/addemp", methods=['POST'])
def AddEmp():
    image_url = url_for('static', filename='background.png')
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    primary_skill = request.form['primary_skill']
    location = request.form['location']

  
    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        
        cursor.execute(insert_sql,(emp_id, first_name, last_name, primary_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('addempoutput.html', name=emp_name, color=color_codes[COLOR], my_name = MY_NAME)

@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    image_url = url_for('static', filename='background.png')
    return render_template("getemp.html", background_image = image_url, my_name = MY_NAME)

@app.route("/fetchdata", methods=['GET','POST'])
def FetchData():
    emp_id = request.form['emp_id']

    output = {}
    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location from employee where emp_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql,(emp_id))
        result = cursor.fetchone()
        
        # Add No Employee found form
        output["emp_id"] = result[0]
        output["first_name"] = result[1]
        output["last_name"] = result[2]
        output["primary_skills"] = result[3]
        output["location"] = result[4]
        
    except Exception as e:
        print(e)

    finally:
        cursor.close()

    return render_template("getempoutput.html", id=output["emp_id"], fname=output["first_name"],
                           lname=output["last_name"], interest=output["primary_skills"], location=output["location"], color=color_codes[COLOR], my_name = MY_NAME)

if __name__ == '__main__':
    #Download the image from s3
    download_image(BACKGROUND_IMAGE)
    # Check for Command Line Parameters for color
    parser = argparse.ArgumentParser()
    parser.add_argument('--color', required=False)
    args = parser.parse_args()

    if args.color:
        print("Color from command line argument =" + args.color)
        COLOR = args.color
        if COLOR_FROM_ENV:
            print("A color was set through environment variable -" + COLOR_FROM_ENV + ". However, color from command line argument takes precendence.")
    elif COLOR_FROM_ENV:
        print("No Command line argument. Color from environment variable =" + COLOR_FROM_ENV)
        COLOR = COLOR_FROM_ENV
    else:
        print("No command line argument or environment variable. Picking a Random Color =" + COLOR)

    # Check if input color is a supported one
    if COLOR not in color_codes:
        print("Color not supported. Received '" + COLOR + "' expected one of " + SUPPORTED_COLORS)
        exit(1)

    app.run(host='0.0.0.0',port=81,debug=True)