FROM odoo:17.0

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       wkhtmltopdf \
       fontconfig \
       fonts-dejavu-core \
       libxrender1 \
       libxext6 \
       libx11-6 \
    && rm -rf /var/lib/apt/lists/* \
    && if [ -x /usr/bin/wkhtmltopdf ]; then ln -sf /usr/bin/wkhtmltopdf /usr/local/bin/wkhtmltopdf || true; fi

USER odoo
