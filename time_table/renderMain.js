function renderMain(data) {
    console.log(data);
    const minutes = toMinutes(data);
    console.log(minutes);
    const hours = toHours(minutes);
    const days = toDays(hours);
    // console.log(days);
    const letterPriority = Object.fromEntries(new Map(
        data["idle_editor_log"]["data"]["letter_priority"].split("")
            .map(function (letter, index) {
                return [letter, index];
            })
    ));
    const userToLetter = data["slack_messages"]["data"]["user_to_letter"];
    const pathToLetter = data["idle_editor_log"]["data"]["path_to_letter"];
    // console.log(letterPriority);
    const mainDiv = document.getElementById("main");
    mainDiv.innerHTML = Object.entries(days).map(function (item) {
        return [dayStartHourOffsetSinceEpoch(item[0]), item];
    }).sort(_sort).map(function (item) {
        return item[1];
    }).map(function (item) {
        return renderDay(item, letterPriority);
    }).join("");
    const selectedChatsRenderer =
        new SelectedChatsRenderer(
            minutes,
            document.getElementById("chat"),
            userToLetter,
            pathToLetter
        );
    const selector = new Selector({
        "main": function (selections) {
            selectedChatsRenderer.render(selections);
        },
        "chat": function (selections) {
            console.log(selections); // object, starts with 1
            renderTimes([selections[1]["start"], selections[1]["end"]]);
        }
    });
    document.addEventListener("selectionchange", function (event) {
        selector.onSelectionChange(event);
    });
}

function toMinutes(data) {
    const minutes = {};
    const userToLetterOuter = data["slack_messages"]["data"]["user_to_letter"];
    const config = [
        [
            "idle_editor_log",
            data["idle_editor_log"]["data"]["history"],
            function (item) {
                // console.log(item);
                const k = item[0], v = item[1],
                    letter = v["letter"], _time = k / 1000;
                return {"letter": letter, "time_start": _time, "time_end": _time};
            },
        ],
        [
            "slack_messages",
            data["slack_messages"]["data"]["history"],
            function (item, userToLetter = userToLetterOuter) {
                const k = item[0], v = item[1],
                    _time = v[0], message = v[1];
                const user = (
                    message.hasOwnProperty("user")
                    && message["user"]
                    || null
                );
                const letter = (
                    user
                    && userToLetter.hasOwnProperty(user)
                    && userToLetter[user]
                    || null
                )
                return {"letter": letter, "time_start": _time, "time_end": _time};
            },
        ],
        [
            "time_log",
            data["time_log"]["data"],
            function (item) {
                const v = item[1];
                const timeStart = datetimeToUtcSeconds(v["start_at"]),
                    timeEnd = datetimeToUtcSeconds(v["end_at"]);
                const getLetter = function (v, timeStart, timeEnd) {
                    const taskId = v["task_id"],
                        jiraProject = v["jira_project"],
                        label = v["label"],
                        isChat = (
                            ((taskId === 72) && (jiraProject === "TIPS"))
                            || ((taskId === 1489) && (jiraProject === "TDS"))
                            || (label && ["chat", "call", "logging"].some(function (start) {
                                return label.substring(0, start.length + 1) === start + " ";
                            }))
                        );
                    switch (true) {
                        case timeStart === timeEnd:
                            return "|";
                        case taskId === null:
                            return "!";
                        case isChat:
                            return "-";
                        default:
                            return "*";
                    }
                };
                return {
                    "letter": getLetter(v, timeStart, timeEnd),
                    "time_start": timeStart,
                    "time_end": timeEnd,
                };
            }
        ],
    ];
    config.forEach(function (configItem) {
        const minuteEntryKey = configItem[0],
            configItemData = configItem[1],
            itemFunction = configItem[2];
        Object.entries(configItemData).forEach(function (item) {
            const itemFunctionResult = itemFunction(item),
                // itemMinutes = itemFunctionResult["minutes"],
                letter = itemFunctionResult["letter"],
                time_start = itemFunctionResult["time_start"],
                time_end = itemFunctionResult["time_end"],
                v = item[1];
            // if (time_start > time_end) {
            //     console.log(item);
            // }
            const itemMinutes = rangeFromTo(timeToMinute(time_start), timeToMinute(time_end) + 1);
            itemMinutes.forEach(function (minute) {
                if (!minutes.hasOwnProperty(minute)) {
                    minutes[minute] = {"letters": {}};
                }
                if (letter) {
                    minutes[minute]["letters"][letter] = null;
                }
                if (!minutes[minute].hasOwnProperty(minuteEntryKey)) {
                    minutes[minute][minuteEntryKey] = {};
                }
                const entry = minutes[minute][minuteEntryKey];
                entry[time_end] = v;
            });
        });
    });
    return minutes;
}

function timeToMinute(seconds) {
    return Math.floor(seconds / 60);
}

function group(minutes, remainder, whole) {
    const hours = {};
    Object.entries(minutes).forEach(function (item) {
        const minuteSinceEpoch = parseInt(item[0]), value = item[1];
        const minute = remainder(minuteSinceEpoch),
            hour = whole(minuteSinceEpoch);
        if (!hours.hasOwnProperty(hour)) {
            hours[hour] = {};
        }
        hours[hour][minute] = value;
    });
    return hours;
}

function toHours(minutes) {
    return group(
        minutes,
        function (minuteSinceEpoch) {
            return minuteSinceEpoch % 60;
        },
        function (minuteSinceEpoch) {
            return Math.floor(minuteSinceEpoch / 60);
        }
    );
}

function toDays(hours) {
    const toDate = function (hourSinceEpoch) {
        return new Date(hourSinceEpoch * 60 * 60 * 1000);
    };
    return group(
        hours,
        function (hourSinceEpoch) {
            return toDate(hourSinceEpoch).getHours();
        },
        function (hourSinceEpoch) {
            const _date = toDate(hourSinceEpoch);
            return "(" + ([
                _date.getFullYear().toString(),
                (_date.getMonth() + 1).toString(),
                _date.getDate().toString()
            ].join(", ")) + ")";
        }
    );
}

function renderDay(item, letterPriority) {
    const k = item[0], v = item[1];
    const res = [
        k,
        "   " + (range(6).map(function (i) {
            return i.toString().repeat(10);
        }).join("")),
        "   " + (range(10).map(function (i) {
            return i.toString();
        }).join("").repeat(6)),
    ].concat(Object.entries(v).sort(_sort).map(renderHour(k, letterPriority)));
    return res.map(function (line) {
        return [
            "<div>",
            line,
            "</div>",
        ].join("")
    }).join("");
}

// https://stackoverflow.com/a/10050831
const range = function (n) {
    return Array.apply(null, Array(n))
        .map(function (_, i) {
            return i;
        });
    // return [...Array(n).keys()];
};

const rangeFromTo = function (start, end_plus_1) {
    return range(end_plus_1 - start).map(function (i) {
        return i + start;
    });
};

const _sort = function (item1, item2) {
    return parseInt(item1[0]) - parseInt(item2[0]);
};

function dayStartHourOffsetSinceEpoch(dayKey) {
    const yearMonthDate =
        dayKey.substring(1, dayKey.length - 1).split(", ").map(function (x) {
            return parseInt(x);
        });
    const _date = new Date(yearMonthDate[0], yearMonthDate[1] - 1, yearMonthDate[2]);
    const dayStartHourOffsetSinceEpochValue =
        Math.floor(_date.getTime() / (60 * 60 * 1000));
    return dayStartHourOffsetSinceEpochValue;
}

function renderHour(dayKey, letterPriority) {
    const dayStartHourOffsetSinceEpochValue = dayStartHourOffsetSinceEpoch(dayKey);
    return function (item) {
        const k = item[0], v = item[1],
            hour = dayStartHourOffsetSinceEpochValue + parseInt(k);
        return [
            "<span>",
            k.padStart(2, " "),
            " ",
            "</span>",
            "<span data-hour=\"", hour.toString(), "\">"
        ].concat(
            renderMinutes(v, letterPriority),
            [
                "</span>",
            ]
        ).join("");
    }
}

function renderMinutes(minutes, letterPriority) {
    return range(60).map(function (minute) {
        if (
            !minutes.hasOwnProperty(minute)
            || !minutes[minute].hasOwnProperty("letters")
            || (Object.keys(minutes[minute]["letters"]).length === 0)
        ) {
            return ".";
        }
        return minByPriority(minutes[minute]["letters"], letterPriority);
    }).join("");
}

function minByPriority(letters, letterPriority) {
    return Object.keys(letters).reduce(function (acc, letter) {
        return letterPriority[acc] < letterPriority[letter] ? acc : letter;
    })
}

function datetimeToUtcSeconds(s) {
    const _time =
        s.substring("datetime.datetime(".length, s.length - 1)
            .split(", ").map(function (i) {
            return parseInt(i);
        });
    const year = _time[0],
        month = _time[1],
        date = _time[2],
        hour = _time[3],
        minute = _time[4],
        second = _time[5] || 0,
        microseconds = _time[6] || 0;
    const d = new Date();
    d.setUTCFullYear(year, month - 1, date);
    d.setUTCHours(hour, minute, second, 0);
    return Math.floor(d.getTime() / 1000 + 0.5).toString() + "." +
        (microseconds.toString().padStart(6, "0"));
}
