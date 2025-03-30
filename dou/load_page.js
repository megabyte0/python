var vacancies = {};
function loadPage(callback) {
    console.log('loadPage');
    var page_size = 20;
    var ids = vacancyIds.slice(listStart, listStart + page_size);
    if (ids.length === 0) {
        return;
    }
    var ids_string = ids.join(',');
    get("/api/vacancies/" + ids_string, null, function (data) {
        data.forEach(function (vacancy) {
            vacancies[vacancy.id] = vacancy;
        });
        document.getElementById('contents').innerHTML += data.map(render_vacancy).join("\n");
        listStart += page_size;
        callback();
    });
}