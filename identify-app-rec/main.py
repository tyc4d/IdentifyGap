from flask import Flask,render_template,request
from google.cloud import storage
import google.cloud.logging
# import the necessary packages
from scipy.spatial import distance as dist
from imutils import perspective
from imutils import contours
import numpy as np
import imutils
import uuid,base64,cv2,os
from ast import literal_eval
app = Flask(__name__)
storage_client = storage.Client.from_service_account_json('creds.json')
client = google.cloud.logging.Client.from_service_account_json('creds-logging.json')
logger = client.logger(name="iden-app")

def upload_to_bucket(blob_name, path_to_file, bucket_name):
    """ Upload data to a bucket"""
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file)
    blob.make_public()
    return blob.public_url
def create_folder_bucket(path,bucket_name):
    """ Upload data to a bucket"""
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(path+'/')
    blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')
    return blob.public_url
def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            source_blob_name, bucket_name, destination_file_name
        )
    )
def delete_blob(bucket_name, blob_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    generation_match_precondition = None

    # Optional: set a generation-match precondition to avoid potential race conditions
    # and data corruptions. The request to delete is aborted if the object's
    # generation number does not match your precondition.
    blob.reload()  # Fetch blob metadata to use in generation_match_precondition.
    generation_match_precondition = blob.generation

    blob.delete(if_generation_match=generation_match_precondition)

    print(f"Blob {blob_name} deleted.")
@app.route('/', methods = ['GET', 'POST'])
def process():
    envelope = request.get_json()
    if not envelope:
        msg = "no Pub/Sub message received"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    if not isinstance(envelope, dict) or "message" not in envelope:
        msg = "invalid Pub/Sub message format"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    pubsub_message = envelope["message"]

    psname = "World"
    if isinstance(pubsub_message, dict) and "data" in pubsub_message:
        psname = base64.b64decode(pubsub_message["data"]).decode("utf-8").strip()
    logger.log(f"Hello {psname}!")
    psname = literal_eval(psname)
    if request.method == 'POST':
        fn = psname["name"]
        download_blob("identifygap-upload",psname["name"],f"/tmp/{fn}")
        try:
            upload_all(rec(f"/tmp/{fn}",1.05),fn)
            delete_blob("identifygap-upload",psname["name"])
            return ("OK",204)
        except:
            print("err",500)
            return "FALSE"
    else:
        return "Pls Use Post"
def upload_all(files,fn):
    create_folder_bucket(fn.split('.')[0],"identifygap-process")
    for path in files:
        filepath = fn.split('.')[0]+'/'+path
        realpath = f"/tmp/{path}"
        upload_to_bucket(filepath,realpath,"identifygap-process")
def midpoint(ptA, ptB):
	return ((ptA[0] + ptB[0]) * 0.5, (ptA[1] + ptB[1]) * 0.5)
# construct the argument parse and parse the arguments
def resize_img(img):

    scale_percent = 50 # 要放大縮小幾%
    width = int(img.shape[1] * scale_percent / 100) # 縮放後圖片寬度
    height = int(img.shape[0] * scale_percent / 100) # 縮放後圖片高度
    dim = (width, height) # 圖片形狀 
    resize_img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)  

    return resize_img
def rec(image_path,width):
	# load the image, convert it to grayscale, and blur it slightly
    image = cv2.imread(image_path)
    image = resize_img(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 0)
    # perform edge detection, then perform a dilation + erosion to
    # close gaps in between object edges
    edged = cv2.Canny(gray, 50, 100)
    edged = cv2.dilate(edged, None, iterations=1)
    edged = cv2.erode(edged, None, iterations=1)
    # find contours in the edge map
    cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    # sort the contours from left-to-right and initialize the
    # 'pixels per metric' calibration variable
    (cnts, _) = contours.sort_contours(cnts)
    pixelsPerMetric = None
    fileaddrs = []
    # loop over the contours individually
    for c in cnts:
        # if the contour is not sufficiently large, ignore it
        if cv2.contourArea(c) < 100:
            continue
        # compute the rotated bounding box of the contour
        orig = image.copy()
        box = cv2.minAreaRect(c)
        box = cv2.cv.BoxPoints(box) if imutils.is_cv2() else cv2.boxPoints(box)
        box = np.array(box, dtype="int")
        # order the points in the contour such that they appear
        # in top-left, top-right, bottom-right, and bottom-left
        # order, then draw the outline of the rotated bounding
        # box
        box = perspective.order_points(box)
        cv2.drawContours(orig, [box.astype("int")], -1, (0, 255, 0), 2)
        # loop over the original points and draw them
        for (x, y) in box:
            cv2.circle(orig, (int(x), int(y)), 5, (0, 0, 255), -1)
        # unpack the ordered bounding box, then compute the midpoint
        # between the top-left and top-right coordinates, followed by
        # the midpoint between bottom-left and bottom-right coordinates
        (tl, tr, br, bl) = box
        (tltrX, tltrY) = midpoint(tl, tr)
        (blbrX, blbrY) = midpoint(bl, br)
        # compute the midpoint between the top-left and top-right points,
        # followed by the midpoint between the top-righ and bottom-right
        (tlblX, tlblY) = midpoint(tl, bl)
        (trbrX, trbrY) = midpoint(tr, br)
        # draw the midpoints on the image
        cv2.circle(orig, (int(tltrX), int(tltrY)), 5, (255, 0, 0), -1)
        cv2.circle(orig, (int(blbrX), int(blbrY)), 5, (255, 0, 0), -1)
        cv2.circle(orig, (int(tlblX), int(tlblY)), 5, (255, 0, 0), -1)
        cv2.circle(orig, (int(trbrX), int(trbrY)), 5, (255, 0, 0), -1)
        # draw lines between the midpoints
        cv2.line(orig, (int(tltrX), int(tltrY)), (int(blbrX), int(blbrY)),
            (255, 0, 255), 2)
        cv2.line(orig, (int(tlblX), int(tlblY)), (int(trbrX), int(trbrY)),
            (255, 0, 255), 2)
        # compute the Euclidean distance between the midpoints
        dA = dist.euclidean((tltrX, tltrY), (blbrX, blbrY))
        dB = dist.euclidean((tlblX, tlblY), (trbrX, trbrY))
        # if the pixels per metric has not been initialized, then
        # compute it as the ratio of pixels to supplied metric
        # (in this case, inches)
        if pixelsPerMetric is None:
            pixelsPerMetric = dB / width
        # compute the size of the object
        dimA = dA / pixelsPerMetric * 2.54
        dimB = dB / pixelsPerMetric * 2.54
        # draw the object sizes on the image
        cv2.putText(orig, "{:.2f}cm".format(dimB),
            (int(tltrX - 15), int(tltrY - 10)), cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (255, 255, 255), 1)
        cv2.putText(orig, "{:.2f}cm".format(dimA),
            (int(trbrX + 10), int(trbrY)), cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (255, 255, 255), 1)
        # show the output image
        #cv2.imshow("Image", orig)
        fileaddr = 'rec_' + str(uuid.uuid4()) + '.png'
        cv2.imwrite(f"/tmp/{fileaddr}",orig)
        fileaddrs.append(fileaddr)
    print(fileaddrs)
        #cv2.waitKey(0)
    return fileaddrs


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8081)))