window.onerror = function(message, source, lineno, colno, error) {
    post_json("/api/log_error", null, {
        message: message,
        source: source,
        lineno: lineno,
        colno: colno,
        stack: error ? error.stack : null
    });
};