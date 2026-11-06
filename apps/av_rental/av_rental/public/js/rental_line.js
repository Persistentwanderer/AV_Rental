frappe.ui.form.on("Rental Line", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		const group = __("Hire");
		frm.add_custom_button(__("Issue"), () => qty_action(frm, __("Issue"), "av_rental.api.issue_lines"), group);
		frm.add_custom_button(
			__("Partial return"),
			() => qty_action(frm, __("Partial return"), "av_rental.api.partial_return"),
			group
		);
		frm.add_custom_button(
			__("Record damage"),
			() => qty_action(frm, __("Record damage"), "av_rental.api.record_damage"),
			group
		);
		frm.add_custom_button(__("Extend"), () => extend_action(frm), group);
	},
});

function qty_action(frm, title, method) {
	frappe.prompt(
		[
			{ fieldname: "qty", fieldtype: "Float", label: __("Qty"), reqd: 1 },
			{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
		],
		(values) => {
			line_call(frm, method, {
				reason: values.reason,
				lines: [{ rental_line: frm.doc.name, qty: values.qty }],
			});
		},
		title,
		__("Confirm")
	);
}

function extend_action(frm) {
	frappe.prompt(
		[
			{ fieldname: "qty", fieldtype: "Float", label: __("Qty"), reqd: 1 },
			{ fieldname: "extended_until", fieldtype: "Datetime", label: __("Extended until"), reqd: 1 },
			{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
		],
		(values) => {
			line_call(frm, "av_rental.api.extend_lines", {
				reason: values.reason,
				extended_until: values.extended_until,
				lines: [{ rental_line: frm.doc.name, qty: values.qty }],
			});
		},
		__("Extend line"),
		__("Extend")
	);
}

function line_call(frm, method, args) {
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
