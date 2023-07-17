function render(data) {
    //console.log(data,typeof data);
    if (data instanceof Array) {
        return data.map(render);
    }
    if ((typeof data === "string") || (data instanceof String)) { //https://stackoverflow.com/a/9436948
        return document.createTextNode(data);
    }
    if (data instanceof Object) {
        var tag = data["tag"];
        var res;
        if (data["xmlns"] === undefined) {
            res = document.createElement(tag);
        } else {
            res = document.createElementNS(data["xmlns"],tag);
        }
        Object.keys(data).forEach(function (key) {
            if (key === "tag") {
                return true;
            }
            var item = data[key];
            if ((typeof item === "string") || (item instanceof String)) {
                res.setAttribute(key, item);
            }
            if (item instanceof Array) {
                var children = render(item);
                //console.log(children);
                children.forEach(function (child) {
                    res.appendChild(child);
                });
            }
        })
        return res;
    }
}
