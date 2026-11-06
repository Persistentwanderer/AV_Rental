app_name = "av_rental"
app_title = "AV Rental"
app_publisher = "Issac"
app_description = (
    "Dry-hire AV and lighting rental: nested gear lists and append-only hire events on ERPNext."
)
app_email = "issac@example.invalid"
app_license = "MIT"

required_apps = ["erpnext"]

# Desk buttons are Client Scripts synced from public/js. That works on the
# production image without a separate `bench build` of this app's assets.
after_install = "av_rental.install.after_install"
after_migrate = "av_rental.install.after_migrate"

add_to_apps_screen = [
    {
        "name": "av_rental",
        "logo": "/assets/erpnext/images/erpnext-logo.svg",
        "title": "AV Rental",
        "route": "/app/av-rental",
        "has_permission": "av_rental.api.has_app_permission",
    }
]
