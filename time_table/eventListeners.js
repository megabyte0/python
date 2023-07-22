function attachEventListeners() {
    // const selector = new Selector();
    // document.addEventListener("selectionchange", function (event) {
    //     selector.onSelectionChange(event);
    // });

    // const rectSizer = new RectResizer(document.getElementById("send"));
    // document.addEventListener("mousedown", function (event) {rectSizer.startTracking(event);});
    // document.addEventListener("mouseup", function (event) {rectSizer.stopTracking(event);});
    // document.addEventListener("mousemove", function (event) {rectSizer.sizeOrLeftTop(event);});
    // document.addEventListener("mousedown", console.log);
    // document.addEventListener("mouseup", console.log);
    // 624, 83, 985, 376
    document.getElementById("send").addEventListener("click", send);
}

class RectResizer {
    constructor(elem) {
        this.elem = elem;
        this.sizing = false;
        this.top = elem.offsetTop;
        this.left = elem.offsetLeft;
        this.x = elem.offsetWidth + elem.offsetLeft;
        this.y = elem.offsetHeight + elem.offsetTop;
        console.log(elem);
    }

    startTracking(event) {
        this.sizing = true;
        this.sizeOrLeftTop(event);
    }

    stopTracking(event) {
        this.sizing = false;
    }

    getXYFromEvent(event) {
        return {
            "x": event.clientX,
            "y": event.clientY,
        };
    }

    size(event) {
        if (!this.sizing) {
            return;
        }
        const xy = this.getXYFromEvent(event);
        this.x = xy.x;
        this.y = xy.y;
        this.applyStyleWidthHeight();
    }

    applyStyleWidthHeight() {
        this.elem.style.width = (this.x - this.left).toString() + "px";
        this.elem.style.height = (this.y - this.top).toString() + "px";
    }

    applyStyleLeftTop() {
        this.elem.style.left = (this.left).toString() + "px";
        this.elem.style.top = (this.top).toString() + "px";
    }

    leftTop(event) {
        if (!this.sizing) {
            return;
        }
        const xy = this.getXYFromEvent(event);
        this.left = xy.x;
        this.top = xy.y;
        this.applyStyleLeftTop();
        this.applyStyleWidthHeight();
    }

    sizeOrLeftTop(event) {
        if (!this.sizing) {
            return;
        }
        const xy = this.getXYFromEvent(event);
        const distanceLeftTop = this.distanceSquared(xy, {"x": this.left, "y": this.top});
        const distanceRightBottom = this.distanceSquared(xy, {"x": this.x, "y": this.y});
        console.log(distanceLeftTop, distanceRightBottom);
        if (distanceLeftTop < distanceRightBottom) {
            this.leftTop(event);
        } else {
            this.size(event);
        }
    }

    distanceSquared(xy1, xy2) {
        return Math.pow(xy1.x - xy2.x, 2) + Math.pow(xy1.y - xy2.y, 2)
    }
}

class Selector {
    constructor(selectionChangeCallBackById) {
        this.selectionChangeCallBackById = selectionChangeCallBackById;
        this.selections = Object.fromEntries(new Map(
            Object.keys(selectionChangeCallBackById).map(function (id) {
                return [id, {}];
            })
        ));
    }

    onSelectionChange(event) {
        const selection = document.getSelection();
        console.log("onSelectionChange", selection);
        Object.entries(this.selectionChangeCallBackById).forEach(function (item) {
            const id = item[0], selectionChangeCallBack = item[1],
                elem = document.getElementById(id);
            // console.log("onSelectionChange forEach", item, elem);
            if (![selection.anchorNode, selection.focusNode].every(function (_node) {
                return elem.contains(_node);
            })) {
                // console.log([selection.anchorNode, selection.focusNode].map(function (_node) {
                //     return elem.contains(_node);
                // }));
                return;
            }
            if (selection.type !== "Range") {
                this.selections[id] = {};
                return;
            }
            if (selection.rangeCount < this.selections.length) {
                this.selections[id] = {};
            }
            this.adjustSelection(selection, id);
            selectionChangeCallBack(this.selections[id]);
        }, this);
    }

    adjustSelection(selection, id) {
        const anchor = this.convertToUtcMinute(
                selection.anchorNode, selection.anchorOffset
            ),
            focus = this.convertToUtcMinute(
                selection.focusNode, selection.focusOffset
            );
        const rangeCount = selection.rangeCount;
        if (anchor < focus) {
            this.selections[id][rangeCount.toString()] = (
                {"start": anchor, "end": focus}
            );
        } else {
            this.selections[id][rangeCount.toString()] = (
                {"start": focus, "end": anchor}
            );
        }
    }

    convertToUtcMinute(node, offset) {
        let variable;
        switch (true) {
            case !!(variable = node.dataset && node.dataset.times):
                return variable;
            case !!(variable = node.parentNode.dataset.hour):
                return parseInt(variable) * 60 + offset;
            case !!(variable = node.parentNode.parentNode.querySelector("[data-hour]").dataset.hour):
                return parseInt(variable) * 60;
        }
    }
}

function send() {
    const timeStartSpan = document.getElementById("time-start"),
        timeEndSpan = document.getElementById("time-end");
    if (!(timeStartSpan && timeEndSpan)) {
        return;
    }
    const commentElem = document.getElementById("comment");
    const message = commentElem.value;
    let taskId, comment;
    if (message.length === 0) {
        taskId = null;
        comment = null;
    } else {
        const messageSplit = message.split(" ");
        if (/^\d+$/.test(messageSplit[0])) {
            taskId = parseInt(messageSplit[0]);
            comment = messageSplit.slice(1).join(" ") || null;
        } else {
            taskId = null;
            comment = message;
        }
    }
    const timeStart = timeStartSpan.innerText, timeEnd = timeEndSpan.innerText;
    const data = {
        "label": comment,
        "task_id": taskId,
        "start_at": timeStart,
        "end_at": timeEnd,
    };
    post(baseUrl+"/api/insert/", "POST", data, function () {
        commentElem.value = "";
    });
}