from flask import Flask,render_template,request
from gcloud import storage
import os

app = Flask(__name__)
 
def upload_to_bucket(blob_name, path_to_file, bucket_name):
    """ Upload data to a bucket"""
     
    # Explicitly use service account credentials by specifying the private key
    # file.
    storage_client = storage.Client.from_service_account_json('creds.json')
    #print(buckets = list(storage_client.list_buckets())
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file)
    
    #returns a public url
    return blob.public_url

@app.route('/')
def root():
   return render_template('index.html')

@app.route('/upload', methods = ['GET', 'POST'])
def upload_file():
   if request.method == 'POST':
      if request.files['file'] == NULL:
         return 'Fail'
      f = request.files['file']
      f.save(f.filename)
      upload_to_bucket()
      return '成功上傳檔案' 
   else:
      return '<a href="../" >Go Back</a>'
   
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)