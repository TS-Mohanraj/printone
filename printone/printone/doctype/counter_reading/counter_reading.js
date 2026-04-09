frappe.ui.form.on('Counter Reading', {

    reading_date: function(frm) {
        run_calculation(frm);
    },

    bnw_count: function(frm) {
        run_calculation(frm);
    },

    color_count: function(frm) {
        run_calculation(frm);
    },

    customer: function(frm) {
        run_calculation(frm);
    },

    contract: function(frm) {
        run_calculation(frm);
    },

    validate: function(frm) {
        if (frm._date_error) {
            frappe.throw("Reading date must be greater than previous reading date");
        }

        let bnw_used = frm.doc.bnw_consumption || 0;
        let color_used = frm.doc.color_consumption || 0;

        let prev_bnw = frm.doc.previous_bnw_consumptiona4 || 0;
        let prev_color = frm.doc.previous_color_consumptiona4 || 0;

        if (prev_bnw > 0 || prev_color > 0) {

            let prev_bnw_90 = prev_bnw * 0.90;
            let prev_bnw_110 = prev_bnw * 1.10;

            let prev_color_90 = prev_color * 0.90;
            let prev_color_110 = prev_color * 1.10;

            if (bnw_used < prev_bnw_90) {
                frappe.throw("BnW Consumption is too low. It should not be less than 90% of previous consumption");
            }

            if (bnw_used > prev_bnw_110) {
                frappe.throw("BnW Consumption is too high. It should not exceed 110% of previous consumption.");
            }

            if (color_used < prev_color_90) {
                frappe.throw("Color Consumption is too low. It should not be less than 90% of previous consumption.");
            }

            if (color_used > prev_color_110) {
                frappe.throw("Color Consumption is too high. It should not exceed 110% of previous consumption.");
            }
        }
    }
});
frappe.ui.form.on('Sales Invoice',{
    onload: function(frm){
        if(!frm.is_new()){
            frm.refresh_fields();
        }
    }
})

function run_calculation(frm) {

    // stop if contract is not selected
    if (!frm.doc.contract) return;

    // convert current date if available
    let current_date = frm.doc.reading_date
        ? frappe.datetime.str_to_obj(frm.doc.reading_date)
        : null;

    // fetch latest previous reading based on contract
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Counter Reading",
            filters: {
                contract: frm.doc.contract,
                name: ["!=", frm.doc.name || ""],
                reading_date: ["<", frm.doc.reading_date || "9999-12-31"]
            },
            fields: [
                "bnw_count",
                "color_count",
                "reading_date",
                "bnw_consumption",
                "color_consumption"
            ],
            order_by: "reading_date desc",
            limit_page_length: 1
        },
        callback: function(r) {

            let prev = r.message.length ? r.message[0] : null;

            let prev_bnw = prev ? (prev.bnw_count || 0) : 0;
            let prev_color = prev ? (prev.color_count || 0) : 0;
            let prev_date = prev ? frappe.datetime.str_to_obj(prev.reading_date) : null;
            let prev_bnw_consumption = prev ? (prev.bnw_consumption || 0) : 0;
            let prev_color_consumption = prev ? (prev.color_consumption || 0) : 0;

            // set previous reading values in form
            frm.set_value("previous_bnw", prev_bnw);
            frm.set_value("previous_color", prev_color);
            frm.set_value("previous_reading_date", prev ? prev.reading_date : null);

            let days = 0;

            // calculate day difference if both dates exist
            if (prev_date && current_date) {

                days = frappe.datetime.get_diff(current_date, prev_date);
                frm.set_value("days_difference", days);

                // validate date order
                if (current_date <= prev_date) {
                    frm._date_error = true;

                    frappe.msgprint({
                        title: "Invalid Date",
                        message: `Current reading date must be greater than previous (${prev.reading_date})`,
                        indicator: "red"
                    });

                    return;
                } else {
                    frm._date_error = false;
                }

                // warn if less than 25 days
                if (days < 25) {
                    frappe.msgprint(`At least 25 days is required, since the last reading. Currently, only ${days} days have passed from previous reading date.`);
                }

            } else {
                frm._date_error = false;
                frm.set_value("days_difference", 0);
            }

            // calculate consumption
            let bnw_used = 0;
            let color_used = 0;

            if (prev) {
                bnw_used = (frm.doc.bnw_count || 0) - prev_bnw;
                color_used = (frm.doc.color_count || 0) - prev_color;
            } else {
                bnw_used = (frm.doc.bnw_count || 0);
                color_used = (frm.doc.color_count || 0);
            }

            // prevent negative values
            bnw_used = Math.max(0, bnw_used);
            color_used = Math.max(0, color_used);

            frm.set_value("bnw_consumption", bnw_used);
            frm.set_value("color_consumption", color_used);

            // fetch contract details
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Printer Contract",
                    name: frm.doc.contract
                },
                callback: function(res) {

                    let contract = res.message;

                    let free_bnw = contract.monthly_free_copies_bnw || 0;
                    let free_color = contract.monthly_free_copies_color || 0;

                    let bnw_rate = contract.extra_rate_bnw || 0;
                    let color_rate = contract.extra_rate_color || 0;

                    let allowed_bnw = 0;
                    let allowed_color = 0;
                    let prorated_bnw = 0;
                    let prorated_color = 0;

                    // apply allowance logic
                    if (!prev || days >= 30) {
                        allowed_bnw = free_bnw;
                        allowed_color = free_color;
                    } else {
                        prorated_bnw = (free_bnw / 30) * days;
                        prorated_color = (free_color / 30) * days;

                        allowed_bnw = prorated_bnw;
                        allowed_color = prorated_color;
                    }

                    // calculate billable copies
                    let bnw_billable = Math.max(0, bnw_used - allowed_bnw);
                    let color_billable = Math.max(0, color_used - allowed_color);

                    // calculate amount
                    let bnw_amount = bnw_billable * bnw_rate;
                    let color_amount = color_billable * color_rate;

                    // set calculated values
                    frm.set_value("prorated_bnw", prorated_bnw);
                    frm.set_value("prorated_color", prorated_color);

                    frm.set_value("bnw_billable", Math.floor(bnw_billable));
                    frm.set_value("color_billable", Math.floor(color_billable));

                    frm.set_value("previous_bnw_consumptiona4", prev_bnw_consumption);
                    frm.set_value("previous_color_consumptiona4", prev_color_consumption);

                    frm.set_value("bnw_amount", bnw_amount);
                    frm.set_value("color_amount", color_amount);
                }
            });
        }
    });
}