frappe.ui.form.on('Printer Contract', {
    onload: function(frm) { toggle_combined_fields(frm); },
    refresh: function(frm) { toggle_combined_fields(frm); },
    combined: function(frm) { toggle_combined_fields(frm); }
});

function toggle_combined_fields(frm) {
    let is_combined = frm.doc.combined ? 1 : 0;

    frm.set_df_property('combined_free_copies', 'hidden', is_combined ? 0 : 1);
    frm.set_df_property('combined_excess_rate', 'hidden', is_combined ? 0 : 1);

    frm.set_df_property('monthly_free_copies_bnw', 'hidden', is_combined ? 1 : 0);
    frm.set_df_property('monthly_free_copies_color', 'hidden', is_combined ? 1 : 0);
    frm.set_df_property('extra_rate_bnw', 'hidden', is_combined ? 1 : 0);
    frm.set_df_property('extra_rate_color', 'hidden', is_combined ? 1 : 0);

    frm.refresh_fields([
        'combined_free_copies', 'combined_excess_rate',
        'monthly_free_copies_bnw', 'monthly_free_copies_color',
        'extra_rate_bnw', 'extra_rate_color'
    ]);
}