// CloudFront Function (viewer-request) on the S3 behaviour only.
// /products/42 -> /index.html ; /assets/app.js and /images/x.jpg pass through.
function handler(event) {
  var request = event.request;
  var uri = request.uri;
  var last = uri.substring(uri.lastIndexOf('/') + 1);
  if (last.indexOf('.') === -1) {
    request.uri = '/index.html';
  }
  return request;
}
