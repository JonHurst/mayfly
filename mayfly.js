"use strict";

function register_service_worker() {
    if (!'serviceWorker' in navigator) return;
    navigator.serviceWorker.register('/sw.js').then(
        function(registration) {
            // Registration was successful
            console.log('ServiceWorker registration successful with scope: ',
                        registration.scope);
        },
        function(err) {
            // registration failed :(
            console.log('ServiceWorker registration failed: ', err);
        });
}

var lookup;


function services_box_changed(event) {
    var c;
    //reset bins
    var bins = document.getElementsByClassName("bin");
    for(c = 0; c < bins.length; c++) {
        bins[c].classList.remove("selected");
    }
    //highlight any bins associated with services
    var i = document.getElementById("services");
    var services = i.value.split(" ");
    for(c = 0; c < services.length; c++) {
        if(!services[c]) continue;
        var service = services[c];
        if(service in lookup) {
            var id_array = lookup[service];
            for(var e = 0; e < id_array.length; e++) {
                var b = document.getElementById(id_array[e]);
                b.classList.add("selected");
            }
        }
    }
}



function toggle_service_listing(event) {
    var target = event.target.nextSibling.nextSibling;
    target.classList.toggle("hidden");
}


window.onload = function() {
    var i = document.getElementById("services");
    i.value = "";
    i.addEventListener("input", services_box_changed);
    i.addEventListener("keyup", function(event) {
        if(event.keyCode === 13) i.blur();
    });
    var c;
    var l = document.getElementsByClassName("arr");
    for(c = 0; c < l.length; c++)
        l[c].addEventListener("click", toggle_service_listing);
    l = document.getElementsByClassName("dep");
    for(c = 0; c < l.length; c++)
        l[c].addEventListener("click", toggle_service_listing);
    if(!navigator.onLine) {
        document.getElementById("title").appendChild(
            document.createTextNode(" (offline)"));
    }
    register_service_worker();
};
