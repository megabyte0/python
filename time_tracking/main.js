function renderMain(data) {
    window["data"] = data;
    window["index_by_id"] = Object.fromEntries(new Map(
        data.map(((value, index) => [value["id"], index]))
    ));
    console.log(data);
    var main = document.getElementById("main");
    main.innerHTML = (data.map(render_item_to_li)
            .join("") + (
            "<li data-id=\"0\" id=\"add\">" + renderItem({
                "start_at": null,
                "end_at": null,
                "label": null,
                "task_id": null,
            }) + "</li>"
        )
    );
    main.addEventListener("click", event_dispatcher);
    main.addEventListener("change", event_dispatcher);
}

const render_item_to_li = x => "<li data-id=\"" + x["id"] + "\">" + renderItem(x) + "</li>";

function renderItem(item) {
    var res = [
        item["start_at"] !== null ? renderTime(item["start_at"]) : "",
        item["start_at"] === item["end_at"] ? "" : renderTime(item["end_at"]),
        item["label"] === null ? "<input type='text' data-type='label' />" : item["label"],
        "<input type='text' value='" +
        (item["task_id"] === null ? "" : item["task_id"]) +
        "' data-type='task_id' />",
        "<span class='action' data-type='action'>" + (
            (item["start_at"] === item["end_at"]) && item["start_at"] ? "Pause" : "Start"
        ) + "</span>"
    ];
    var _class = item["exported"] ? " class=\"exported\"" : "";
    return "<ul" + _class + ">" + (res.map(x => "<li>" + x + "</li>").join("")) + "</ul>";
}

function renderTime(s) {
    var x = s.substring("datetime.datetime(".length, s.length - 1).split(", ");
    while (x.length < 7) {
        x.push("0");
    }
    var date = new Date(
        `${x[0]}-${x[1].padStart(2, "0")}-${x[2].padStart(2, "0")}T` +
        `${x[3].padStart(2, "0")}:${x[4].padStart(2, "0")}:${x[5].padStart(2, "0")}` +
        `.${x[6].padStart(6, "0")}Z`
    );
    return [date.getHours(), date.getMinutes(), date.getSeconds()].map(
        x => x.toString().padStart(2, "0")
    ).join(":");
}

function event_dispatcher(event) {
    //console.log(event.type, event.target);
    var target = event.target;
    var type = event.type;
    var data_type = ("type" in target.dataset) && target.dataset.type;
    const type_by_action = {"label": "change", "task_id": "change", "action": "click"};
    if (!(data_type && type_by_action[data_type] === type)) {
        return;
    }
    var id = target.parentElement.parentElement.parentElement.dataset["id"];
    var value = (type === "change") ? target.value : null;
    if ((id.toString() === "0") && (data_type !== "action")) {
        return
    }
    console.log(data_type, id, value);
    var item;
    if (id.toString() !== "0") {
        item = data[index_by_id[id]];
    } else {
        var ul = target.parentElement.parentElement;
        var children = ul.children;
        const null_if_empty = x => x === "" ? null : x;
        item = {
            "label": null_if_empty(children[2].children[0].value),
            "task_id": null_if_empty(children[3].children[0].value),
        }
    }
    if (["label", "task_id"].some(field => field === data_type)) {
        var item_copy = object_copy(item);
        item_copy[data_type] = value === "" ? null : value;
        update_log(item_copy);
    }
    if (data_type === "action") {
        if ((id.toString() === "0") || (item["start_at"] !== item["end_at"])) {
            start_log(item);
        } else {
            pause_log(item);
        }
    }
}

function append_item(item) {
    console.log("append_item", item);
    data.push(item);
    index_by_id[item["id"]] = data.length - 1;
    var main = document.getElementById("main");
    var add = document.getElementById("add");
    var to_add = document.createElement("li");
    to_add.dataset["id"] = item["id"];
    to_add.innerHTML = renderItem(item);
    console.log(main, add, to_add);
    main.insertBefore(to_add, add);
}

function change_item(item) {
    var main = document.getElementById("main");
    var li = null;//document.querySelector("li[data-id=" + item["id"] + "]");
    for (var index = 0; index < main.children.length; ++index) {
        var child = main.children[index];
        if (("id" in child.dataset) && (child.dataset["id"] == item["id"])) {
            li = child;
            break;
        }
    }
    if (li === null) {
        return;
    }
    data[index_by_id[item["id"]]] = item;
    li.innerHTML = renderItem(item);
}

function start_log(item) {
    var item_copy = object_copy(item);
    if (!(item_copy["id"])) {
        delete item_copy["id"];
    }
    post(baseUrl + "/api/start/", "POST", item, data => append_item(data[0]));
}

function update_log(item) {
    post(baseUrl + "/api/update/", "POST", item, data => change_item(data[0]));
}

function pause_log(item) {
    post(baseUrl + "/api/stop/" + item["id"], "POST", item, data => change_item(data[0]));
}

const object_copy = item => Object.fromEntries(new Map(
    Object.keys(item).map(key => [key, item[key]])
));