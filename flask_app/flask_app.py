from tools.modules.database_scripts.patientVariantTable import patientVariantTable
from tools.modules.database_scripts.variantAnnotationsTable import variantAnnotationsTable
from flask import Flask, render_template, request
import os

# Create the Flask app — templates in 'templates' folder
app = Flask(__name__, template_folder='templates')

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Build path: one level up + "data/uploads"
UPLOAD_FOLDER = os.path.join(current_dir, '..', 'data')

# Make sure the folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Flask
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def upload():
    print("Request method:", request.method)  

    if request.method == 'POST':
        file = request.files.get('vcf')  

        if not file:
            return "No file uploaded", 400

        if not file.filename.endswith('.vcf'):
            return "Invalid file type. Please upload a VCF file.", 400

        # Save the file inside the uploads folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        folder_path = os.path.dirname(file_path)

        # Get the absolute path for use in your scripts
        abs_file_path = os.path.abspath(file_path)
        patientVariantTable(folder_path)
        variantAnnotationsTable(folder_path)

        return render_template('success.html', file_path=abs_file_path)

    # GET request: show the upload form
    return render_template('uploads.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)