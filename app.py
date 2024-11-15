from flask import Flask, request, jsonify, render_template, url_for
from flask_cors import CORS
import os
from datetime import datetime
import requests
import mysql.connector
import cloudinary
import cloudinary.uploader

app = Flask(_name_)
CORS(app, resources={r"/": {"origins": ""}})

@app.route('/')
def home():
    return render_template('index.html') # Allow CORS for all origins

# Ensure the uploads directory exists
upload_dir = os.path.join(os.path.dirname(_file_), "uploads")
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)

# Imagga API credentials
imagga_api_key = 'acc_7cc6ab937af8e86'
imagga_api_secret = 'f2cb99611314dc9ea8895ffa6f8b3b1f'

# Cloudinary configuration
cloudinary.config(
    cloud_name='dsu0qscmi',
    api_key='587969486239771',
    api_secret='kycH-OrMBfTCWG6dJs1Rzqczdt4',
    secure=True
)

# MySQL database connection
db = mysql.connector.connect(
    host="autorack.proxy.rlwy.net",
    user="root",
    password="kgbQryjqbVQFojvZRoMrAPMAHvHCAQer",
    database="railway",
    port=49449
)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(upload_dir, filename)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = f"captured_image_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Upload the image to Cloudinary and get the public URL
        public_url = cloudinary.uploader.upload(filepath)['secure_url']
        if not public_url:
            return jsonify({'error': 'Image upload to Cloudinary failed'}), 500

        return jsonify({'message': 'Image uploaded successfully!', 'filename': filename, 'url': public_url}), 200

@app.route('/process-images', methods=['POST'])
def process_images():
    results = []
    for filename in os.listdir(upload_dir):
        if filename.endswith(".jpg"):
            filepath = os.path.join(upload_dir, filename)

            # Upload the image to Cloudinary to get the public URL
            public_url = cloudinary.uploader.upload(filepath)['secure_url']
            if not public_url:
                results.append({'item': 'Image upload to Cloudinary failed', 'tag': 'Image upload to Cloudinary failed'})
                continue

            # Use the public URL for image recognition with Imagga API
            response = requests.get(
                'https://api.imagga.com/v2/tags',
                params={'image_url': public_url},
                auth=(imagga_api_key, imagga_api_secret)
            )

            if response.status_code == 200:
                tags = response.json().get('result', {}).get('tags', [])
                if tags:
                    top_tag = tags[0]['tag']['en']
                    results.append({'item': top_tag, 'tag': top_tag})
                else:
                    results.append({'item': 'No tags found', 'tag': 'No tags found'})
            else:
                results.append({'item': 'Image recognition failed', 'tag': 'Image recognition failed'})

    return jsonify({'results': results}), 200

@app.route("/add-items", methods=["POST"])
def add_items():
    data = request.json
    cursor = db.cursor()

    try:
        for item_data in data:
            item_name = item_data.get("itemName")
            quantity = item_data.get("quantity")

            cursor.execute("SELECT * FROM Inventory WHERE Item = %s", (item_name,))
            item = cursor.fetchone()
            if item:
                # Item exists, update the quantity
                new_quantity = int(item[1]) + int(quantity)
                cursor.execute("UPDATE Inventory SET Quantity = %s WHERE Item = %s", (new_quantity, item_name))
            else:
                # Item does not exist, insert a new row
                cursor.execute("INSERT INTO Inventory (Item, Quantity) VALUES (%s, %s)", (item_name, quantity))

            db.commit()
        return jsonify({"message": "Items added/updated successfully"}), 200
    except Exception as e:
        print("Error:", e)
        db.rollback()
        return jsonify({"error": "Error adding/updating items"}), 500
    finally:
        cursor.close()

if _name_ == "_main_":
    app.run(debug=True)
