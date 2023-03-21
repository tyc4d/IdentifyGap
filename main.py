from flask import Flask,render_template,request
from google.cloud import storage

import os,uuid

app = Flask(__name__)
storage_client = storage.Client.from_service_account_json('creds.json')

class CFolder:
    # 建構式
    def __init__(self, name, created_time):
        self.name = name
        self.created_time = created_time 
class CFile:
    # 建構式
    def __init__(self, name, created_time, size, content_type,public_url):
        self.name = name
        self.created_time = created_time 
        self.size = size
        self.content_type = content_type
        self.public_url = public_url

def upload_to_bucket(blob_name, path_to_file, bucket_name):
    """ Upload data to a bucket"""
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file)
    return blob.public_url
def list_blobs(bucket_name):
    """Lists all the blobs in the bucket."""

    blobs = storage_client.list_blobs(bucket_name)
    return blobs


@app.route('/')
def root():
   return render_template('index.html')

@app.route('/upload', methods = ['GET', 'POST'])
def upload_file():
   if request.method == 'POST':
      fn = ""
      f = request.files['file']
      fn = f"{str(uuid.uuid1())}-{f.filename}"
      f.save(f"/tmp/{fn}")
      
      return '<p>成功上傳檔案 '+upload_to_bucket(fn,f"/tmp/{fn}","identifygap-upload")+'<p><a href="../" >Go Back</a>' 
   else:
      return '<a href="../" >Go Back</a>'

@app.route('/view')
def view_files():
    if not request.args:
        blobs = list_blobs("identifygap-process")
        folders = []
        for blob in blobs:
            if blob.size == 0:
                tmp = CFolder(blob.name,blob.time_created)
                folders.append(tmp)
        print(folders)
        return render_template('view_folder.html', data=folders)
    else:
        blobs = list_blobs("identifygap-process")
        files = []
        for blob in blobs:
            if request.args['id'] in blob.name:
                tmp = CFile(blob.name,blob.time_created,blob.size,blob.content_type,blob.public_url)
                files.append(tmp)
        files = files[1::]
        return render_template('view.html', data=files,id=request.args['id'])




if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)