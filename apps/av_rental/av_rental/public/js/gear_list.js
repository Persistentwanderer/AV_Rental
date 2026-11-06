frappe.ui.form.on("Gear List", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		const group = __("Hire");
		frm.add_custom_button(
			__("Issue outstanding"),
			() => {
				ask_reason(__("Issue gear list"), __("Dispatch outstanding gear on this list and its children"), (reason) => {
					hire_call(frm, "av_rental.api.issue_gear_list", {
						gear_list: frm.doc.name,
						reason,
					});
				});
			},
			group
		);
		frm.add_custom_button(
			__("Partial return"),
			() => line_qty_dialog(frm, __("Partial return"), "av_rental.api.partial_return"),
			group
		);
		frm.add_custom_button(
			__("Record damage"),
			() => line_qty_dialog(frm, __("Record damage"), "av_rental.api.record_damage"),
			group
		);
		frm.add_custom_button(
			__("Extend list"),
			() => {
				frappe.prompt(
					[
						{
							fieldname: "extended_until",
							fieldtype: "Datetime",
							label: __("Extended until"),
							reqd: 1,
						},
						{
							fieldname: "reason",
							fieldtype: "Small Text",
							label: __("Reason"),
							reqd: 1,
						},
					],
					(values) => {
						hire_call(frm, "av_rental.api.extend_gear_list", {
							gear_list: frm.doc.name,
							extended_until: values.extended_until,
							reason: values.reason,
						});
					},
					__("Extend gear list"),
					__("Extend")
				);
			},
			group
		);
	},
});

function ask_reason(title, seed, done) {
	frappe.prompt(
		[
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason"),
				reqd: 1,
				default: seed,
			},
		],
		(values) => done(values.reason),
		title,
		__("Confirm")
	);
}

function line_qty_dialog(frm, title, method) {
	frappe.prompt(
		[
			{
				fieldname: "rental_line",
				fieldtype: "Link",
				options: "Rental Line",
				label: __("Rental Line"),
				reqd: 1,
				get_query() {
					return {
						query: "av_rental.api.rental_line_link_query",
						filters: { gear_list: frm.doc.name },
					};
				},
			},
			{ fieldname: "qty", fieldtype: "Float", label: __("Qty"), reqd: 1 },
			{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
		],
		(values) => {
			hire_call(frm, method, {
				gear_list: frm.doc.name,
				reason: values.reason,
				lines: [{ rental_line: values.rental_line, qty: values.qty }],
			});
		},
		title,
		__("Confirm")
	);
}

function hire_call(frm, method, args) {
	frappe.call({
		method,
		args,
		freeze: true,
		callback(response) {
			if (!response.exc) {
				frappe.show_alert({ message: __("Hire event recorded"), indicator: "green" });
				frm.reload_doc();
			}
		},
	});
}
