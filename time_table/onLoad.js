const baseUrl = (
    //"http://localhost:8000"
    ""
);

const onLoad = function () {
    // https://stackoverflow.com/a/9456144/
    const secondsSinceEpoch = //Math.floor((new Date()).getTime() / 1000 - 4 * 7 * 24 * 60 * 60);
        Math.floor((new Date(2023,5,19, 0)).getTime() / 1000);
    const dataUrl = (
        baseUrl + "/api/data/"
    );
    get(dataUrl + secondsSinceEpoch.toString(), "GET", renderMain);
    attachEventListeners(); // runs before renderMain
    //renderMain();
}

//http://xahlee.info/js/js_scritping_svg_basics.html
if (window.addEventListener) {
    window.addEventListener("load", onLoad, false);
} else { // IE
    window.attachEvent("onload", onLoad);
}
