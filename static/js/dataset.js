var Dataset = {
    selected: [],
    clickedCheckbox: function(el, fname, ftoken) {
        console.log("Nazwa pliku:", fname);
        console.log("Token pliku:", ftoken);
        found = Dataset.selected.filter(v => v.token == ftoken);
        if (found.length > 0) {
            el.checked = false;
            Dataset.selected = Dataset.selected.filter(v => v.token != ftoken);
        } else {
            el.checked = true;
            Dataset.selected.push({ name: fname, token: ftoken })
        }

        Dataset.rebuildList();

        console.log("Dataset.selected:", Dataset.selected);
        if (Dataset.selected.length > 0) {
            $('#dataset-fixed').show("slow");
        } else {
            $('#dataset-fixed').hide("slow");
        }
    },
    closeFixed: function(e) {
        Dataset.selected.map(function(v) {
            var chk = document.getElementById("chk-" + v.token);
            if (chk) {
                chk.checked = false;
            }            
        });
        Dataset.selected = [];
        if (e)
            e.preventDefault();
        $('#dataset-fixed').hide("slow");
    },
    rebuildList: function() {
        var list = document.getElementById("dataset-fixed-items");
        console.log("Rebuilding list", list);
        while (list.firstChild) {            
            list.firstChild.remove();
        }
        Dataset.selected.map(function(v) {
            var li = document.createElement("li");
            li.appendChild(document.createTextNode(v.name));
            list.appendChild(li);
        });
    },
    histogram: function() {
        /* Czy wymuaszym ponowne obliczenie? */
        let forceRecalculate = false
        elForcerecalculate = document.getElementById("force-recalculate-histogram");
        if (elForcerecalculate) {
            forceRecalculate = elForcerecalculate.checked;
        }

        /* Scalamy identyfikatory. */ 
        var items = Dataset.selected.map(v => v.token).join(','); 
        var extraParams = "";
        if (forceRecalculate) {
            extraParams += "?forceRecalculate=true";
        }
        var res = fetch("/histogram/"+items+extraParams)
                    .then( (res) => res.json())
                    .then( jsonRes => {
                            if (jsonRes.result == 'failure') {
                                showModalInfo(jsonRes.message);
                            } else {
                                if (!jsonRes.data || !jsonRes.data.task_id) {
                                    console.log("Odpowiedź z zserwera: ", jsonRes);
                                    showModalInfo("Błędna odpowiedź serwera. Oczekiwałem res.data.task_id. " +
                                                  "Proszę skontaktować się z administratorami systemu.");
                                } else  
                                    window.open("/dash_histograms/?task_id="+jsonRes.data.task_id, target="_blank");
                            }
                        })
                    .catch( (err) => {
                        showModalInfo(err);
                    });
    }
}
