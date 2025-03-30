    function load_vacancy(elem) {
        console.log(elem);
        var p = elem.parentNode, id = p.id;
        get("/api/vacancy/"+id,null,function(data){
            // descr=parent(data,{'id':"job-description"},-1);
            var old_child = p.childNodes[p.childElementCount - 3];
            p.replaceChild(recreate_html(data),old_child);
        });
    }

    function recreate_html(x) {
        var res;
        if (x['tag']) {
            res = document.createElement(x['tag']);
            if (x['attrs']) {
                Object.keys(x['attrs']).forEach(function(attr) {
                    res.setAttribute(attr, x['attrs'][attr]);
                });
            }
            if (x['children']) {
                x['children'].map(recreate_html).forEach(function(elem) {
                    res.appendChild(elem);
                });
            }
        }
        if (x['data']) {
            res = document.createTextNode(x['data']);
        }
        return res;
    }
