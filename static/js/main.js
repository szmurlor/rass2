function showArchived() {
    var elements = document.getElementsByClassName("archived");
    for (var i=0; i < elements.length; i++) {
        var e = elements[i];
        e.style.display = '';
    }
    document.getElementById('show-archived').style.display='none';
    document.getElementById('hide-archived').style.display = '';
}

function hideArchived() {
    console.log("Trying to hide.");
    var elements = document.getElementsByClassName("archived");
    for (var i=0; i < elements.length; i++) {
        var e = elements[i];
        e.style.display = 'none';
        console.log("Hiding: ", e);
    }
    document.getElementById('show-archived').style.display = '';
    document.getElementById('hide-archived').style.display = 'none';
}

// initialization on document end
(function() {
    hideArchived();
 })();