function clearContents() {
    document.getElementById("contents").innerHTML = "";
}

var vacancyIds = [];
var listStart = 0;
var loading = false;

function getIds(callback) {
    get("/api/ids", null, function (data) {
        // vacancyIds.length = 0;
        // vacancyIds.push(...data);
        vacancyIds = data;
        listStart = 0;
        callback();
    });
}

function onLoad() {
    clearContents();
    getIds(function () {
        startObserver(document.getElementById('end_reached'), function () {
            if (loading) {
                console.log('stop loading as in progress');
                return;
            }
            loading = true;
            console.log('set loading to true');
            loadPage(function () {
                loading = false;
                console.log('set loading to false');
                get_render_title_stats();
            });
        });
    });
}