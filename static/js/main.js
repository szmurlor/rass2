function showArchived() {
    var elements = document.getElementsByClassName("archived");
    for (var i=0; i < elements.length; i++) {
        var e = elements[i];
        e.style.display = '';
    }
    document.getElementById('show-archived').display = 'none';
    document.getElementById('hide-archived').display = '';
}

function hideArchived() {
    console.log("Trying to hide.");
    var elements = document.getElementsByClassName("archived");
    for (var i=0; i < elements.length; i++) {
        var e = elements[i];
        e.style.display = 'none';
        console.log("Hiding: ", e);
    }
    document.getElementById('show-archived').display = '';
    document.getElementById('hide-archived').display = 'none';
}

// initialization on document end
(function() {
    hideArchived();
 })();