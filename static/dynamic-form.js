$(function() {
    $("div[data-id=dynamic-list]").each(function() {
        var $this = $(this);

        //Add new entry
        $this.find("button[data-id=add-row]").click(function() {
            var oldrow = $this.find("[data-id=list-entry]:last");
            var row = oldrow.clone(true, true);
            var elem_id = row.find(":input")[0].id;
            var elem_num = parseInt(elem_id.replace(/.*-(\d{1,4})/m, '$1')) + 1;
            row.attr('data-id', 'list-entry');
            row.find(":input").each(function() {
                var id = $(this).attr('id').replace('-' + (elem_num - 1), '-' + (elem_num));
                $(this).attr('name', id).attr('id', id).val('');
            });
            oldrow.after(row);
        });

        //Remove row
        $this.find("button[data-id=remove-row]").click(function() {
            if($this.find("[data-id=list-entry]").length > 1) {
                var thisRow = $(this).closest("[data-id=list-entry]");
                thisRow.remove();
            }
        });
    });
});