function startObserver(element, callback) {
    if ("IntersectionObserver" in window) {
        var intersectionObserver = new IntersectionObserver(function (entries) {
            // If intersectionRatio is 0, the target is out of view
            // and we do not need to do anything.
            entries.forEach(function (entry) {
                if (entry.intersectionRatio > 0) {
                    callback();
                }
                console.log('intersection observer', entry.intersectionRatio);
            });
        });
        intersectionObserver.observe(element);
    }
    element.addEventListener('mousedown', callback);
}