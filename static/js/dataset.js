var Dataset = {
    clickedCheckbox: function(el, fuid) {
        $('#dataset-fixed').show("slow");
    },
    closeFixed: function(e) {
        e.preventDefault();
        $('#dataset-fixed').hide("slow");
    }
}
