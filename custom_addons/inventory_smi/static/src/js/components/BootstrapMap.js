/** @odoo-module **/
import { Component, useState, mount, whenReady, xml } from "@odoo/owl";
import { templates } from "@web/core/assets";
import { MapWidget } from "@inventory_smi/js/components/MapWidget";

export class DenahPage extends Component {
    static template = xml`
        <div class="smi-denah-wrapper">

            <div class="smi-card">

                <!-- Header -->
                <div class="smi-card__header">

                    <span class="smi-card__title">
                        Denah Lengkap Gudang
                    </span>

                    <button class="smi-btn smi-btn--sm"
                            t-att-class="state.modeTampilan === 'add_point'
                                ? 'smi-btn smi-btn--danger smi-btn--sm'
                                : 'smi-btn smi-btn--primary smi-btn--sm'"
                            t-on-click="toggleAddMode">

                        <t t-esc="state.modeTampilan === 'add_point'
                            ? 'Batal Tambah'
                            : '+ Tambah Titik'"/>

                    </button>

                </div>

                <!-- Body -->
                <div class="smi-card__body" style="padding:16px;">

                    <MapWidget mode="state.modeTampilan"
                            onNewPoint="(coords) => this.handleNewPoint(coords)"
                            onPointSelected="(p) => this.handlePointSelected(p)"/>

                </div>

                <!-- Legend -->
                <div style="padding:0 16px 16px;">
                    <div style="display:flex;gap:12px;margin-top:10px;font-size:11px;color:var(--text-muted);">

                        <span>
                            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10B981;margin-right:4px;"></span>
                            Aman
                        </span>

                        <span>
                            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#F59E0B;margin-right:4px;"></span>
                            Sedikit
                        </span>

                        <span>
                            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#94A3B8;margin-right:4px;"></span>
                            Kosong
                        </span>

                    </div>
                    
                </div>

            </div>

        </div>
    `;

    static components = { MapWidget };

    setup() {
        this.state = useState({
            modeTampilan: 'view'
        });
    }

    toggleAddMode() {
        this.state.modeTampilan = this.state.modeTampilan === 'add_point' ? 'view' : 'add_point';
    }

    async handleNewPoint(coords) {
        const name = prompt("Masukkan Nama Titik Penyimpanan:");
        if (!name) {
            this.state.modeTampilan = 'view';
            return;
        }

        const payload = {
            name: name,
            koordinat_x: coords.x,
            koordinat_y: coords.y,
            deskripsi: `Ditambahkan via peta pada ${new Date().toLocaleString()}`
        };

        try {
            const formData = new FormData();
            for (const key in payload) {
                formData.append(key, payload[key]);
            }

            const response = await fetch('/smi/api/inventory_points', {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                window.location.reload();
            } else {
                const err = await response.json();
                alert("Gagal menambahkan titik: " + (err.error || "Unknown Error"));
            }
        } catch (error) {
            console.error(error);
            alert("Koneksi gagal. Pastikan server Odoo berjalan.");
        }
    }

    handlePointSelected(point) {
        if (window.showPointPanel) {
            window.showPointPanel(point.id);
        }
    }
}

whenReady(() => {
    // mount for Dashboard Page
    const dashTarget = document.getElementById('smi_map_root');
    if (dashTarget) {
        mount(MapWidget, dashTarget, {
            templates,
            props: {
                mode: 'view',
                onPointSelected: (point) => {
                    if (window.showPointPanel) {
                        window.showPointPanel(point.id);
                    }
                }
            }
        });
    }

    // mount for Denah Page
    const fullTarget = document.getElementById('smi_full_map_root');
    if (fullTarget) {
        mount(DenahPage, fullTarget, { templates });
    }
});