class SelectedChatsRenderer {
    constructor(minutes, elem, userToLetter, pathToLetter) {
        this.minutes = minutes;
        this.elem = elem;
        this.userToLetter = userToLetter;
        this.pathToLetter = pathToLetter;
        // this.elem.innerHTML = "test";
    }

    render(selections, elem = null) {
        console.log("render", selections);
        const selectedMinutes = this.getSelectedMinutes(selections);
        const selectedMinutesWithChats = Object.fromEntries(new Map(
            Object.entries(selectedMinutes).filter(function (item) {
                return item[1].hasOwnProperty("slack_messages");
            })
        ));
        console.log("render", selectedMinutes);
        const chatEntries = this.extract(
            selectedMinutesWithChats,
            this.getReduceExtractChats(this.userToLetter)
        );
        const paths = Object.keys(this.pathToLetter);
        const ideLogs = this.extract(
            selectedMinutes,
            this.extractIdeLogs()
        );
        const timeLogs = this.extract(
            selectedMinutes,
            function (acc, minuteValue) {
                if (!minuteValue.hasOwnProperty("time_log")) {
                    return acc;
                }
                const timeLog = minuteValue["time_log"];
                Object.values(timeLog).forEach(function (value) {
                    const id = value["id"];
                    console.log("extract time log", value);
                    acc[id] = value;
                });
                return acc;
            }
        );
        const chatEntriesWithIdeLogs = Object.fromEntries(new Map(
            Object.entries(chatEntries).map(function (item) {
                const _time = item[0], message = item[1];
                return [_time, {
                    "type": "chat",
                    "value": message,
                }];
            }).concat(
                Object.entries(ideLogs).map(function (item) {
                    const fileNameWithFullPath = item[0], times = Object.keys(item[1]);
                    return [times.join(","), {
                        "type": "ide_log",
                        "value": fileNameWithFullPath,
                    }];
                })
            ).concat(
                Object.values(timeLogs).map(function (value) {
                    return [
                        [value["start_at"], value["end_at"]]
                            .map(datetimeToUtcSeconds).join(","), {
                            "type": "time_log",
                            "value": value,
                        }]
                })
            )
        ));
        console.log("render", chatEntriesWithIdeLogs); // entries);
        if (!elem) {
            elem = this.elem;
        }
        console.log("render elem", elem);
        const sortedEntries = Object.entries(chatEntriesWithIdeLogs).sort(_sort);
        if (sortedEntries.length) {
            renderTimes(sortedEntries.map(function (item) {
                const times = item[0];
                return times;
            }));
        }
        const renderedHtml = sortedEntries.map(function (item) {
            const times = item[0], valueCombined = item[1],
                _type = valueCombined["type"], value = valueCombined["value"];
            switch (_type) {
                case "ide_log":
                    return this.renderIdleLogItem(this.cutOffFilePath(paths)(value), times);
                case "chat":
                    const _date = new Date(parseFloat(times) * 1000);
                    return this.renderChatItem(times, _date, value);
                case "time_log":
                    return this.renderTimeLogItem(times, value);
            }
        }, this).join("");
        // console.log("render html", renderedHtml);
        elem.innerHTML = renderedHtml;
        // console.log(elem.innerHtml);
    }

    renderIdleLogItem(fileName, times) {
        return [
            "<div data-times=\"",
            times,
            "\">",
            fileName,
            "</div>",
        ].join("");
    }

    renderChatItem(_time, _date, messageRendered) {
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
        return [
            "<div data-times=\"",
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
    }

    renderTimeLogItem(times, value) {
        const taskId = value["task_id"], jiraProject = value["jira_project"];
        const composedTaskId = taskId && jiraProject && (jiraProject + "-" + taskId) || null;
        return [
            "<div data-times=\"",
            times,
            "\">",
            value["id"].toString(),
            " ",
            composedTaskId,
            " ",
            value["label"],
            "</div>",
        ].join("");
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

    extract(minutes, reduceExtractFunction) {
        return Object.values(minutes).reduce(reduceExtractFunction, {});
    }

    getReduceExtractChats(userToLetter) {
        // console.log("getReduceExtractChats", this);
        return function (acc, value) {
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
        };
    }

    extractIdeLogs() {
        return function(acc, value) {
            if (!value.hasOwnProperty("idle_editor_log")) {
                return acc;
            }
            const ideLogs = value["idle_editor_log"];
            Object.entries(ideLogs).forEach(function (item) {
                const _time = item[0], log = item[1], files = log["files"]; // letter, files
                if (files === undefined) {
                    return;
                }
                files.forEach(function (fileNameWithFullPath) {
                    if (!acc.hasOwnProperty(fileNameWithFullPath)) {
                        acc[fileNameWithFullPath] = {};
                    }
                    acc[fileNameWithFullPath][_time] = null;
                });
            });
            return acc;
        }
    }

    cutOffFilePath(paths) {
        return function (fileName) {
            const pathsStartsWith = paths.filter(function (path) {
                return fileName.substring(0, path.length) === path;
            });
            if (pathsStartsWith.length) {
                return fileName.substring(
                    pathsStartsWith[0].length,
                    fileName.length
                );
            } else {
                return fileName;
            }
        };
    }
}

function renderTimes(timesArray) {
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
        ["time-start", timesArray, function (acc, item) {
            return acc < item ? acc : item;
        }],
        ["time-end", timesArray, function (acc, item) {
            return acc > item ? acc : item;
        }],
    ].map(function (item) {
        const id = item[0], timesArray = item[1],
            reduceFunction = item[2];
        const timeSet = {};
        timesArray.forEach(function (times) {
            times.split(",").forEach(function (_time) {
                timeSet[_time] = null;
            });
        });
        const _time = Object.keys(timeSet).reduce(reduceFunction);
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