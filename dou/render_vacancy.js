function render_vacancy(item) {
    var id = item["id"];
    var score = item["score"];
    var title = item["title"];
    var descr = item["descr"];
    var like = item["like"];
    var done = item["done"];
    return '<div class="item" id="' + id + '"' +
        (score === 0 ? ' style="filter:opacity(30%);"' : '')
        + '>' + (render_header(item) + '<p>' + descr + '</p>') +
        '<div style="display: inline-block; height: 2em; width:100%;" onmousedown="load_vacancy(this);">&gt;&gt;&gt;</div>' +
        '<div style="text-align: center;" class="star_bar">' +
        star_bar(score === null && 10 || score) + '</div>' +
        //'<div style="clear: both;"></div>'+
        '</div>'
}

function render_header(item) {
    var id = item["id"];
    var score = item["score"];
    var title = item["title"];
    var descr = item["descr"];
    var like = item["like"];
    var done = item["done"];
    return '<h3><a href="/api/redirect/' + id + '">' + title + '</a>' +
        '<span style="float: right; padding:4px 4px 4px 8px;">' +
        svg_heart(like) + '</span>' +
        '<span style="float: right; padding:4px 8px 4px 4px;">' +
        svg_tick(done) + '</span>' +
        '</h3>';
}