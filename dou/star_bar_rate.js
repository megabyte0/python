function star_bar(n) {
    var MAX_RATE = 10;
    var res = [['&times;', 0]];
    var i;
    for (i = 1; i <= n; ++i) {
        res.push(['★', i]);
    }
    for (i = n + 1; i <= MAX_RATE; ++i) {
        res.push(['☆', i]);
    }
    return res.map(function (s) {
        return '<span onmousedown="rate(this,' + s[1] + ');">' + s[0] + '</span>';
    }).join('');
}

function rate(elem, n) {
    console.log('rate', elem, n);
    //x=elem;
    var parent = elem.parentNode, id = parent.parentNode.id;
    get("/api/score/" + id + "/" + n, 'POST', function () {
        if (n === 0) {
            hide(parent);
        }
        parent.innerHTML = star_bar(n);
        // ratings[id] = n;
    });
}

function hide(elem) {
    console.log('hide', elem);
    var parent = elem.parentNode, id = parent.id;
    parent.setAttribute('style', 'filter:opacity(30%);');
    //get(`/api/hide/${id}`,'POST');
}
