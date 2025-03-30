var stats = {};
function get_render_title_stats() {
    get("/api/stats", null, function(data) {
        stats = data;
        render_stats();
    })
}

function render_stats() {
    var good = stats["good"],
        seen = stats["seen"],
        last_crawl = stats["last_crawl"];
    var statsArr = [
        good, seen - (seen * 2 > last_crawl ? last_crawl : 0),
    ];
    var statsStr = statsArr.join("/");
    document.title = statsStr;
}