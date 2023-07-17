//https://stackoverflow.com/a/8567149
function loadXMLDoc(url, method, data, callback) {
    var xmlhttp = new XMLHttpRequest();

    xmlhttp.onreadystatechange = function () {
        //console.log(xmlhttp.readyState);
        if (xmlhttp.readyState == XMLHttpRequest.DONE) {   // XMLHttpRequest.DONE == 4
            if ([200, 204].some(x => xmlhttp.status == x)) {
                console.log(url, xmlhttp.status, xmlhttp.responseText)
                callback(xmlhttp.responseText);
            } else if (xmlhttp.status == 400) {
                console.log('There was an error 400');
            } else {
                console.log('something else other than 200 was returned: ' + xmlhttp.status);
            }
        }
    };

    xmlhttp.open(method || "GET", url, true);
    if (data) {
        xmlhttp.send(JSON.stringify(data));
    } else {
        xmlhttp.send();
    }

}

function get(url, method, callback) {
    loadXMLDoc(url, method || "GET", null, function (data) {
        if (callback) {
            callback(data && data !== '' && JSON.parse(data));
        }
    });
}

function post(url, method, data, callback) {
    loadXMLDoc(url, method || "POST", data, function (data) {
        if (callback) {
            callback(data && data !== '' && JSON.parse(data));
        }
    });
}