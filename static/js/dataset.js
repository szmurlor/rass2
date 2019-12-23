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
    histogram: async function() {
        console.log(Dataset.selected);
        var items='';
        Dataset.selected.map(v => {items += v.token + ",";}); 
        var res = await fetch("/histogram/"+items);
        var jsonRes = await res.json();
        console.log(jsonRes);
        if (jsonRes.result == 'failure') {
            showModalInfo(jsonRes.message);
        } else {
         window.open("/histogram/"+items, target="_blank");
        }
    }
}
