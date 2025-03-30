function svg_heart(fill) {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="25" height="24" onmousedown="like(this);"><path d="M7 1C3.65 1 1 3.7 1 7c0 6.75 6.8 8.5 11.4 15.15 4.4-6.6 11.45-8.65 11.45-15.15 0-3.3-2.7-6-6-6-2.4 0-4.5 1.4-5.45 3.45-0.95-2.05-3-3.45-5.4-3.45z" stroke="red" stroke-width="1.5" fill="' + (fill ? 'red' : 'none') + '"/></svg>';
}

function svg_tick(fill) {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="27.3216" height="23.9256" onmousedown="mark_done(this);"><path d="M8.2888 15.9728c-2.0048,-1.3 -6.0384,-3.196 -8.1992,-3.8424 3.0968,3.1552 6.28,7.688 8.664,11.7416 5.5848,-10.4592 12.4968,-17.3288 18.4,-23.7288 -5.3208,3.5488 -15.6376,12.0144 -18.8648,15.8296z" stroke="#008503" stroke-width="0.5" fill="' + (fill ? '#008503' : 'none') + '"/></svg>';
}

function like_done(api, colour, key) {
    return function (elem) {
        console.log(elem);
        var path = elem.children[0];
        var fill = path.getAttribute("fill"), color_dict = {},
            id = elem.parentNode.parentNode.parentNode.id;
        color_dict["none"] = "1";
        color_dict[colour] = "0";
        var rev_dict = {};
        rev_dict["none"] = colour;
        rev_dict[colour] = "none";
        path.setAttribute("fill", rev_dict[fill]);
        get("/api/" + api + "/" + id + "/" + color_dict[fill], "POST");
        vacancies[id][key] = (color_dict[fill] === "1");
    }
}

like = like_done("like", "red", "like");
mark_done = like_done("done", "#008503", "done");
