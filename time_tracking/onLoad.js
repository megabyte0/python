const baseUrl = (
    //'http://localhost:8000'
    ''
);

const onLoad = function () {
    const dataUrl = (
        baseUrl+'/api/data/'
    );
    get(dataUrl, 'GET', renderMain);
    //renderMain();
}

//http://xahlee.info/js/js_scritping_svg_basics.html
if (window.addEventListener) {
    window.addEventListener('load', onLoad, false);
} else { // IE
    window.attachEvent('onload', onLoad);
}
