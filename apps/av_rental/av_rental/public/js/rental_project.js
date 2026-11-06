frappe.ui.form.on("Rental Project", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Effective on hire"), () => {
			frappe.set_route("query-report", "Effective On Hire", {
				rental_project: frm.doc.name,
			});
		});
		frm.add_custom_button(__("Gear lists"), () => {
			frappe.set_route("List", "Gear List", { rental_project: frm.doc.name });
		});
	},
});
