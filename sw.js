"use strict";

var CACHE_NAME = "mayfly_static";
var CACHE_FILES = [
    'mayfly.html',
    'mayfly.css',
    'mayfly.js',
    'ezyheader.gif'
];


function fill_cache(cache) {
    console.log("Writing to mayfly-static cache");
    return cache.addAll(CACHE_FILES);
}


function install_sw(event) {
    console.log("sw install event triggered");
    event.waitUntil(
        self.caches.open(CACHE_NAME).then(fill_cache));
}


function do_fetch(event) {
    console.log("sw fetch event triggered");
    event.respondWith(
        self.fetch(event.request).then(
            function(response) {
                let rclone = response.clone();
                self.caches.open(CACHE_NAME).then(
                    function (cache) {
                        console.log("Cached " + event.request.url);
                        cache.put(event.request, rclone);
                    });
                return response;
            }).catch(
                function() {
                    console.log("Serving " + event.request.url + " from cache");
                    return self.caches.match(event.request);
            })
    );
}

self.addEventListener('install', install_sw);
self.addEventListener('activate', event => {
    event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', do_fetch);
