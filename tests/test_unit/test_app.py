# tests/test_unit/test_flask_app.py

import os
import io
import pytest
from app.app import app  # Correct import: no quotes!

# -------------------------
# Flask test client fixture
# -------------------------
@pytest.fixture
def client():
    """
    Pytest fixture to create a Flask test client.
    This allows us to simulate GET and POST requests without running the server.
    """
    app.config['TESTING'] = True  # Enable testing mode
    with app.test_client() as client:
        yield client

# -------------------------
# Test GET request
# -------------------------
def test_get_upload_page(client):
    """
    Test that a GET request to '/' returns the upload page correctly.
    """
    response = client.get('/')  # Simulate a GET request
    assert response.status_code == 200  # Should return HTTP 200 OK
    assert b'Upload your VCF' in response.data   # Check that the page contains the form heading

# -------------------------
# Test POST with a valid VCF
# -------------------------
def test_post_valid_vcf(client, tmp_path):
    """
    Test uploading a valid VCF file.
    tmp_path is a temporary directory provided by pytest.
    """
    app.config['UPLOAD_FOLDER'] = tmp_path  # Use temporary folder to avoid polluting real uploads

    # Simulate a file upload using io.BytesIO
    data = {
        'vcf': (
            io.BytesIO(b'##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n'),
            'test.vcf'  # Filename of the simulated uploaded file
        )
    }

    # POST request to upload file
    response = client.post('/', data=data, content_type='multipart/form-data')
    
    # Check that the response indicates success
    assert response.status_code == 200
    assert b'File Uploaded Successfully!' in response.data
    
    # Verify that the file exists in the temporary folder
    uploaded_file = tmp_path / 'test.vcf'
    assert uploaded_file.exists()

# -------------------------
# Test POST with no file
# -------------------------
def test_post_no_file(client):
    """
    Test POST request with no file uploaded.
    Should return HTTP 400 and an error message.
    """
    response = client.post('/', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b'No file uploaded' in response.data

# -------------------------
# Test POST with invalid file type
# -------------------------
def test_post_invalid_file_type(client):
    """
    Test uploading a file that is not a VCF.
    Should return HTTP 400 and an error message.
    """
    data = {
        'vcf': (io.BytesIO(b'some content'), 'test.txt')  # Invalid file extension
    }
    response = client.post('/', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b'Invalid file type' in response.data