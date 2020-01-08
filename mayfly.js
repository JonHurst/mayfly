"use strict";

var lookup;


function services_box_changed(event) {
    var c;
    //reset selected bins
    var selected_bins = document.getElementsByClassName("bin");
    for(c = 0; c < selected_bins.length; c++) {
        selected_bins[c].classList.remove("selected");
    }
    //highlight any bins associated with services
    var i = document.getElementById("services");
    var services = i.value.split(" ");
    for(c = 0; c < services.length; c++) {
        if(!services[c]) continue;
        var easy_designators = ["EZY", "EJU", "EZS"];
        for(var d = 0; d < easy_designators.length; d++) {
            var service = easy_designators[d] + services[c];
            if(service in lookup) {
                var id_array = lookup[service];
                for(var e = 0; e < id_array.length; e++) {
                    var b = document.getElementById(id_array[e]);
                    b.classList.add("selected");
                }
            }
        }
    }
}


window.onload = function() {
    var i = document.getElementById("services");
    i.addEventListener("input", services_box_changed);
    i.addEventListener("keyup", function(event) {
        if(event.keyCode === 13) i.blur();
    });
};
