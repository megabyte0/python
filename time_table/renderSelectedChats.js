class SelectedChatsRenderer {
    constructor(minutes, elem, userToLetter) {
        this.minutes = minutes;
        this.elem = elem;
        this.userToLetter = userToLetter;
        // this.elem.innerHTML = "test";
    }

    render(selections, elem = null) {
        console.log("render", selections);
        const selectedMinutes = this.getSelectedMinutes(selections);
        const selectedMinutesWithChats = Object.fromEntries(new Map(
            Object.entries(selectedMinutes).filter(function (item) {
                return item[1].hasOwnProperty("slack_messages");
            })
        ))
        const entries = this.extractChats(selectedMinutesWithChats);
        console.log("render", entries);
        if (!elem) {
            elem = this.elem;
        }
        console.log("render elem", elem);
        // https://stackoverflow.com/a/30970751
        const escape = function(s) {
            const lookup = {
                '&': "&amp;",
                '"': "&quot;",
                '\'': "&apos;",
                '<': "&lt;",
                '>': "&gt;"
            };
            return s.replace( /[&"'<>]/g, function (c) {
                return lookup[c];
            });
        }
        const sortedEntries = Object.entries(entries).sort(_sort);
        if (sortedEntries.length) {
            renderTimes(sortedEntries[0][0], sortedEntries[sortedEntries.length - 1][0]);
        }
        const renderedHtml = sortedEntries.map(function (item) {
            const _time = item[0], _date = new Date(parseFloat(_time) * 1000),
            messageRendered = item[1];
            return [
                "<div data-time=\"",
                _time,
                "\">",
                _date.getHours().toString().padStart(2, "0"),
                ":",
                _date.getMinutes().toString().padStart(2, "0"),
                ":",
                _date.getSeconds().toString().padStart(2, "0"),
                " ",
                escape(messageRendered),
                "</div>",
            ].join("");
        }).join("");
        // console.log("render html", renderedHtml);
        elem.innerHTML = renderedHtml;
        // console.log(elem.innerHtml);
    }

    getSelectedMinutes(selections) {
        // console.log(this);
        const minutes = this.minutes;
        return Object.values(selections).reduce(function (acc, selection) {
            rangeFromTo(selection.start, selection.end).forEach(function (selectionMinute) {
                // console.log("getSelectedMinutes", selectionMinute, minutes.hasOwnProperty(selectionMinute));
                if (minutes.hasOwnProperty(selectionMinute)) {
                    acc[selectionMinute] = minutes[selectionMinute];
                }
                // console.log("getSelectedMinutes", acc);
            });
            return acc;
        }, Object.create(null));
    }

    extractChats(minutes) {
        const userToLetter = this.userToLetter;
        return Object.values(minutes).reduce(function (acc, value) {
            const slackMessages = value["slack_messages"];
            Object.values(slackMessages).forEach(function (item) {
                const _time = item[0], v = item[1];
                if (
                    v.hasOwnProperty("user")
                    && userToLetter.hasOwnProperty(v["user"])
                    && v.hasOwnProperty("text")
                ) {
                    const text = JSON.stringify(v["text"]);
                    acc[_time.toString()] = [
                        userToLetter[v["user"]],
                        " ",
                        text.substring(1, text.length - 1),
                    ].join("");
                }
            })
            return acc;
        }, Object.create(null));

    }
}

function renderTimes(timeStart, timeEnd) {
    const elem = document.getElementById("times");
    const mySqlFormat = function(_time) {
        const timeStrSplit = _time.toString().split("."),
            secondsSinceEpoch = parseInt(timeStrSplit[0]),
            fractionSeconds = timeStrSplit[1] || "0";
        const _date = new Date(secondsSinceEpoch * 1000);
        return [
            _date.getUTCFullYear().toString(),
            "-",
            (_date.getUTCMonth() + 1).toString().padStart(2, '0'),
            "-",
            _date.getUTCDate().toString().padStart(2, '0'),
            " ",
            _date.getUTCHours().toString().padStart(2, '0'),
            ":",
            _date.getUTCMinutes().toString().padStart(2, '0'),
            ":",
            _date.getUTCSeconds().toString().padStart(2, '0'),
        ].concat(timeStrSplit.length > 1 ? [".", fractionSeconds] : []).join("");
    };
    const html = [
        ["time-start", timeStart],
        ["time-end", timeEnd],
    ].map(function (item) {
        const id = item[0], _time = item[1];
        return [
            "<span data-time=\"",
            _time,
            "\" id=\"",
            id,
            "\">",
            mySqlFormat(_time),
            "</span>"
        ].join("");
    }).join("");
    // console.log("renderTimes html", html);
    elem.innerHTML = html;
}