# Official ERPNext image from frappe/frappe_docker, plus the local av_rental app.
# https://github.com/frappe/frappe_docker
# Pin matches frappe_docker example.env at the time this stack was written.
ARG ERPNEXT_VERSION=v16.54.0
FROM frappe/erpnext:${ERPNEXT_VERSION}

USER frappe
WORKDIR /home/frappe/frappe-bench

COPY --chown=frappe:frappe apps/av_rental /home/frappe/frappe-bench/apps/av_rental

# Editable install registers the app with the bench virtualenv.
# sites/apps.txt is rewritten on boot by the configurator (`ls apps`).
RUN /home/frappe/frappe-bench/env/bin/pip install --no-cache-dir --no-deps \
    -e /home/frappe/frappe-bench/apps/av_rental
