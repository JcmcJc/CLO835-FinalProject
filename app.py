from flask import Flask, render_template, request, send_from_directory
from pymysql import connections
import os
import random
import argparse
import boto3
from botocore.exceptions import NoCredentialsError
import shutil


app = Flask(__name__)

# S3 Configuration
S3_BUCKET = os.environ.get("S3_BUCKET", "clo835-finalproject")
S3_IMAGE_PATH = os.environ.get("S3_IMAGE_PATH", "s3://clo835-finalproject/background.png")
LOCAL_IMAGE_PATH = os.path.join('static', 'background.png')

DBHOST = os.environ.get("DBHOST") or "localhost"
DBUSER = os.environ.get("DBUSER") or "root"
DBPWD = os.environ.get("DBPWD") or "password"
DATABASE = os.environ.get("DATABASE") or "employees"
COLOR_FROM_ENV = os.environ.get('APP_COLOR') or "lime"
DBPORT = int(os.environ.get("DBPORT"))

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

# S3 Client Setup
s3_client = boto3.client('s3')

# Ensure static directory exists
os.makedirs('static', exist_ok=True)

# Add this to your existing code
def list_s3_bucket_contents(bucket):
    try:
        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(Bucket=bucket)
        
        print(f"Contents of S3 Bucket: {bucket}")
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"- {obj['Key']}")
        else:
            print("Bucket is empty or you don't have list permissions.")
        
    except Exception as e:
        print(f"Error listing bucket contents: {e}")

# Call this function before trying to download
list_s3_bucket_contents(S3_BUCKET)

def download_image_from_s3(bucket, key, local_path):
    """
    Download an image from S3 to a local path.
    
    :param bucket: S3 bucket name
    :param key: S3 object key (path to the image)
    :param local_path: Local path to save the image
    """
    try:
        # Create S3 client
        s3_client = boto3.client('s3')
        
        # Download the file
        s3_client.download_file(bucket, key, local_path)
        print(f"Successfully downloaded image from S3: {bucket}/{key} to {local_path}")
        return True
    except NoCredentialsError:
        print("Error: AWS credentials not found!")
        return False
    except s3_client.exceptions.NoSuchKey:
        print(f"Error: The specified key {key} does not exist in the bucket {bucket}")
        return False
    except s3_client.exceptions.NoSuchBucket:
        print(f"Error: The specified bucket {bucket} does not exist")
        return False
    except Exception as e:
        print(f"Unexpected error downloading image: {str(e)}")
        return False

def ensure_background_image():
    """
    Ensure the background image is downloaded from S3.
    If download fails, use a default or existing image.
    """
    if not os.path.exists(LOCAL_IMAGE_PATH):
        # Try to download from S3
        success = download_image_from_s3(S3_BUCKET, S3_IMAGE_PATH, LOCAL_IMAGE_PATH)
        
        if not success:
            # Optionally, you could have a default image or skip background
            print("Could not download background image from S3")

# Ensure background image is downloaded on app startup
ensure_background_image()
        
@app.route('/image')
def serve_image():
    image_path = 'static/background.png'
    if os.path.exists(image_path):
        return send_from_directory(os.path.dirname(image_path), os.path.basename(image_path))
    else:
        return "Image not found", 404
        
@app.route("/", methods=['GET', 'POST'])
def home():
    # Fetch the image from S3 and save it locally
    ensure_background_image()
    return render_template('addemp.html', color=color_codes[COLOR])

@app.route("/about", methods=['GET','POST'])
def about():
    # Fetch the image from S3 and save it locally
    download_image_from_s3(S3_IMAGE_PATH, LOCAL_IMAGE_PATH)
    return render_template('about.html', color=color_codes[COLOR])
    
@app.route("/addemp", methods=['POST'])
def AddEmp():
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
    return render_template('addempoutput.html', name=emp_name, color=color_codes[COLOR])

@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    return render_template("getemp.html", color=color_codes[COLOR])


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
                           lname=output["last_name"], interest=output["primary_skills"], location=output["location"], color=color_codes[COLOR])

if __name__ == '__main__':
    
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

    app.run(host='0.0.0.0',port=8080,debug=True)
