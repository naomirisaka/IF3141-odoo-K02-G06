/** @odoo-module **/
import { Component, useState, mount, whenReady, xml } from "@odoo/owl";
import { templates } from "@web/core/assets";
import { MapWidget } from "./MapWidget";

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
                            t-if="canManage"
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

                    <MapWidget
                            materialId="state.materialId"
                            onReady="(api) => this.registerMapApi(api)" mode="state.modeTampilan"
                            onNewPoint="(coords) => this.handleNewPoint(coords)"
                            onPointSelected="(p) => this.handlePointSelected(p)"/>

                </div>

                <!-- Legend -->
                <div style="padding:0 16px 16px;">

                    <div style="display:flex;gap:12px;font-size:11px;color:var(--text-muted);">

                        <span>
                            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#239670;margin-right:4px;"></span>
                            Aman
                        </span>

                        <span>
                            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#CE3737;margin-right:4px;"></span>
                            Sisa Sedikit
                        </span>

                        <span>
                            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#94A3B8;margin-right:4px;"></span>
                            Kosong
                        </span>

                    </div>

                </div>

            </div>

            <!-- ADD POINT MODAL -->
            <t t-if="state.showAddModal">

                <div class="smi-modal-overlay open"
                     t-on-click="closeModalBackdrop">

                    <div class="smi-modal"
                         t-on-click.stop="() => {}">

                        <div class="smi-modal__header">

                            <span class="smi-modal__title">
                                Tambah Titik Inventori
                            </span>

                        </div>

                        <div class="smi-modal__body">

                            <div class="form-group">

                                <label class="form-label">
                                    Nama Titik
                                </label>

                                <input type="text"
                                       class="smi-input"
                                       placeholder="Contoh: Rak A1"
                                       t-model="state.newPointName"/>

                            </div>

                            <div style="display:flex;gap:10px;margin-top:20px;">

                                <button class="smi-btn smi-btn--primary"
                                        t-on-click="savePoint">

                                    Simpan

                                </button>

                                <button class="smi-btn smi-btn--secondary"
                                        t-on-click="closeModal">

                                    Batal

                                </button>

                            </div>

                        </div>

                    </div>

                </div>

            </t>

        </div>
    `;

    static components = { MapWidget };

    setup() {
        this.state = useState({
            modeTampilan: 'view',
            showAddModal: false,
            pendingCoords: null,
            newPointName: '',
            materialId: null,
        });

        const params = new URLSearchParams(window.location.search);
        const materialId = params.get('material_id');

        this.state.materialId = materialId ? parseInt(materialId) : null;

        this.mapApi = null;

        try {
            var dataEl = document.getElementById('smi_map_data');
            this.canManage = dataEl && dataEl.dataset && dataEl.dataset.canManage === '1';
        } catch (e) {
            this.canManage = false;
        }
    }

    refreshMap() {
        try {
            if (this.mapApi && typeof this.mapApi.refresh === 'function') {
                this.mapApi.refresh();
            }
        } catch (e) {
            // ignore
        }
    }

    toggleAddMode() {
        this.state.modeTampilan =
            this.state.modeTampilan === 'add_point'
                ? 'view'
                : 'add_point';
    }

    registerMapApi(api) {
        this.mapApi = api;
    }

    handleNewPoint(coords) {
        this.state.pendingCoords = coords;
        this.state.showAddModal = true;
    }

    closeModal() {
        this.state.showAddModal = false;
        this.state.newPointName = '';
        this.state.pendingCoords = null;
        this.state.modeTampilan = 'view';
    }

    closeModalBackdrop(ev) {
        if (ev.target.classList.contains('smi-modal-overlay')) {
            this.closeModal();
        }
    }

    async savePoint() {
        if (!this.state.newPointName.trim()) {
            return;
        }

        const payload = {
            name: this.state.newPointName,
            koordinat_x: this.state.pendingCoords.x,
            koordinat_y: this.state.pendingCoords.y,
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
                alert("Gagal menambahkan titik.");
            }
        } catch (error) {
            console.error(error);
            alert("Koneksi gagal.");
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
    let dashInstance = null;
    if (dashTarget) {
            dashInstance = mount(MapWidget, dashTarget, {
                templates,
                props: {
                    mode: 'view',
                    materialId: dashTarget.dataset.materialId,
                    onPointSelected: (point) => {
                        try {
                            try { window.__smi_map_selected_point = point; } catch (e) {}
                            var modalEl = document.getElementById('map-modal');
                            var modalOpen = modalEl && modalEl.classList && modalEl.classList.contains('open');

                            if (modalOpen) {
                                return;
                            }
                            
                            if (typeof window.selectInventoryPoint === 'function') {
                                window.selectInventoryPoint(String(point.id), point.name || '');
                            } else if (typeof window.showPointPanel === 'function') {
                                window.showPointPanel(point.id);
                            }
                        } catch (e) {
                            console.error('onPointSelected handler error', e);
                        }
                    }
                }
        });

    }

    // mount for Denah Page
    const fullTarget = document.getElementById('smi_full_map_root');
    let fullInstance = null;
    if (fullTarget) {
        fullInstance = mount(DenahPage, fullTarget, { templates });
    }

    function handlePointDeletedShared(payload) {
        var refreshed = false;
        try {
            if (dashInstance && typeof dashInstance.refresh === 'function') {
                dashInstance.refresh();
                refreshed = true;
            }
        } catch (e) {}
        try {
            if (fullInstance && typeof fullInstance.refreshMap === 'function') {
                fullInstance.refreshMap();
                refreshed = true;
            }
        } catch (e) {}
        if (!refreshed) {
            window.location.reload();
        }
    }

    function trySubscribeBusShared() {
        try {
            const candidates = [window.bus, (window.odoo && window.odoo.bus), (window.core && window.core.bus)];
            for (const b of candidates) {
                if (b && typeof b.on === 'function') {
                    b.on('notification', null, function(msg) {
                        try {
                            var payload = null;
                            if (Array.isArray(msg) && msg[1] && msg[1].payload) payload = msg[1].payload;
                            else if (Array.isArray(msg) && msg[1]) payload = msg[1];
                            else if (msg && msg.payload) payload = msg.payload;
                            if (payload && payload.type === 'point_deleted') {
                                handlePointDeletedShared(payload);
                            }
                        } catch (e) {}
                    });
                    return true;
                }
            }
        } catch (e) {}
        return false;
    }

    if (!trySubscribeBusShared()) {
        // polling fallback: try to refresh maps periodically
        setInterval(function() {
            try { if (dashInstance && typeof dashInstance.refresh === 'function') dashInstance.refresh(); } catch (e) {}
            try { if (fullInstance && typeof fullInstance.refreshMap === 'function') fullInstance.refreshMap(); } catch (e) {}
        }, 12000);
    }
});