from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import requests
import mysql.connector
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Set up uploads directory
upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(upload_dir, exist_ok=True)

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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(upload_dir, filename)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['image']
    if not file.filename:
        return jsonify({'error': 'No selected file'}), 400

    filename = f"captured_image_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    # Upload the image to Cloudinary
    upload_result = cloudinary.uploader.upload(filepath)
    public_url = upload_result.get('secure_url')

    if not public_url:
        return jsonify({'error': 'Image upload to Cloudinary failed'}), 500

    return jsonify({'message': 'Image uploaded successfully!', 'filename': filename, 'url': public_url}), 200

@app.route('/process-images', methods=['POST'])
def process_images():
    results = []
    for filename in os.listdir(upload_dir):
        if filename.endswith(".jpg"):
            filepath = os.path.join(upload_dir, filename)

            # Upload the image to Cloudinary
            upload_result = cloudinary.uploader.upload(filepath)
            public_url = upload_result.get('secure_url')
            if not public_url:
                results.append({'item': 'Image upload failed', 'tag': 'Image upload failed'})
                continue

            # Use Imagga API for image recognition
            response = requests.get(
                'https://api.imagga.com/v2/tags',
                params={'image_url': public_url},
                auth=(imagga_api_key, imagga_api_secret)
            )

            if response.status_code == 200:
                tags = response.json().get('result', {}).get('tags', [])
                top_tag = tags[0]['tag']['en'] if tags else 'No tags found'
                results.append({'item': top_tag, 'tag': top_tag})
            else:
                results.append({'item': 'Image recognition failed', 'tag': 'Image recognition failed'})

    return jsonify({'results': results}), 200

@app.route("/add-items", methods=["POST"])
def add_items():
    data = request.json
    cursor = db.cursor()

    try:
        if not data:
            return jsonify({"error": "No data provided"}), 400

        for item_data in data:
            item_name = item_data.get("itemName")
            quantity = item_data.get("quantity", 1)  # Default to 1 if quantity is missing

            if not item_name:
                return jsonify({"error": "Item name is missing in the payload"}), 400

            # Check if the item exists in the database
            cursor.execute("SELECT Quantity FROM Inventory WHERE Items = %s", (item_name,))
            item = cursor.fetchone()

            if item:
                # Item exists, update the quantity
                new_quantity = int(item[0]) + int(quantity)
                cursor.execute("UPDATE Inventory SET Quantity = %s WHERE Items = %s", (new_quantity, item_name))
            else:
                # Item does not exist, insert a new row
                cursor.execute("INSERT INTO Inventory (Items, Quantity) VALUES (%s, %s)", (item_name, quantity))

        db.commit()
        return jsonify({"message": "Items added/updated successfully"}), 200
    except Exception as e:
        print("Error details:", str(e))  # Log detailed error for debugging
        db.rollback()
        return jsonify({"error": f"Error adding/updating items: {str(e)}"}), 500
    finally:
        cursor.close()

if __name__ == "__main__":
    app.run(debug=True)
