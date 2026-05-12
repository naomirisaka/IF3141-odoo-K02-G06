/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef, xml } from "@odoo/owl";

/**
 * MapWidget — Interactive SVG inventory floor plan.
 *
 * Props:
 *   mode          {String}   'view' | 'pick_input' | 'pick_output' | 'add_point'
 *   materialId    {Number}   optional — filter points by material
 *   onPointSelected {Function} callback(point)
 *   onNewPoint    {Function} callback({x, y}) — add_point mode only
 */
export class MapWidget extends Component {
    static template = xml`
        <div class="smi-map-container"
             t-att-class="{'smi-map-container--add-point': props.mode === 'add_point'}"
             t-on-mousemove="onSvgMouseMove"
             t-on-mouseleave="onSvgMouseLeave">

            <!-- Loading state -->
            <div t-if="state.loading" style="display:flex;align-items:center;justify-content:center;padding:48px;">
                <div class="smi-spinner"/>
            </div>

            <!-- SVG floor plan + point overlay -->
            <svg t-else=""
                 t-ref="svgEl"
                 class="smi-map-svg"
                 viewBox="0 0 800 500"
                 xmlns="http://www.w3.org/2000/svg"
                 t-on-click="onSvgClick">

                <!-- Static floor plan (inlined for reliability) -->
                <rect x="2" y="2" width="796" height="496" rx="10" ry="10" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="3" border-radius="10"/>

                <text x="400" y="22" font-family="Inter,system-ui,sans-serif" font-size="13"
                      fill="#64748B" text-anchor="middle" font-weight="600">
                    CV Dunia Offset Printing — Denah Lantai Produksi
                </text>

                <!-- Machines -->
                <rect x="40"  y="50"  width="160" height="90" fill="#E2E8F0" stroke="#94A3B8" stroke-width="1.5" rx="6"/>
                <text x="120" y="91" font-family="Inter,system-ui,sans-serif" font-size="12" fill="#475569" text-anchor="middle" font-weight="600">Mesin Cetak 1</text>
                <text x="120" y="110" font-family="Inter,system-ui,sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">Offset Printing</text>

                <rect x="240" y="50"  width="160" height="90" fill="#E2E8F0" stroke="#94A3B8" stroke-width="1.5" rx="6"/>
                <text x="320" y="91" font-family="Inter,system-ui,sans-serif" font-size="12" fill="#475569" text-anchor="middle" font-weight="600">Mesin Cetak 2</text>
                <text x="320" y="110" font-family="Inter,system-ui,sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">Offset Printing</text>

                <rect x="40"  y="190" width="150" height="80" fill="#E2E8F0" stroke="#94A3B8" stroke-width="1.5" rx="6"/>
                <text x="115" y="226" font-family="Inter,system-ui,sans-serif" font-size="12" fill="#475569" text-anchor="middle" font-weight="600">Mesin Laminasi</text>
                <text x="115" y="244" font-family="Inter,system-ui,sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">Hot / Cold</text>

                <rect x="40"  y="330" width="150" height="80" fill="#E2E8F0" stroke="#94A3B8" stroke-width="1.5" rx="6"/>
                <text x="115" y="366" font-family="Inter,system-ui,sans-serif" font-size="12" fill="#475569" text-anchor="middle" font-weight="600">Mesin Pond</text>
                <text x="115" y="384" font-family="Inter,system-ui,sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">Die Cutting</text>

                <rect x="240" y="330" width="150" height="80" fill="#E2E8F0" stroke="#94A3B8" stroke-width="1.5" rx="6"/>
                <text x="315" y="366" font-family="Inter,system-ui,sans-serif" font-size="12" fill="#475569" text-anchor="middle" font-weight="600">Mesin Foil</text>
                <text x="315" y="384" font-family="Inter,system-ui,sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">Hot Stamping</text>

                <rect x="600" y="40" width="160" height="110" fill="#EFF6FF" stroke="#93C5FD" stroke-width="1.5" rx="6"/>
                <text x="680" y="88" font-family="Inter,system-ui,sans-serif" font-size="12" fill="#3B82F6" text-anchor="middle" font-weight="600">Gudang Bahan</text>
                <text x="680" y="106" font-family="Inter,system-ui,sans-serif" font-size="10" fill="#93C5FD" text-anchor="middle">Area Penyimpanan</text>

                <rect x="450" y="330" width="160" height="80" fill="#E2E8F0" stroke="#94A3B8" stroke-width="1.5" rx="6"/>
                <text x="530" y="366" font-family="Inter,system-ui,sans-serif" font-size="12" fill="#475569" text-anchor="middle" font-weight="600">Area Finishing</text>
                <text x="530" y="384" font-family="Inter,system-ui,sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">Packaging</text>

                <rect x="600" y="40" width="160" height="220" fill="#EFF6FF" stroke="#93C5FD" stroke-width="1.5" rx="6"/>
                <text x="680" y="138" font-family="Inter,system-ui,sans-serif" font-size="12" fill="#3B82F6" text-anchor="middle" font-weight="600">Gudang Bahan</text>
                <text x="680" y="156" font-family="Inter,system-ui,sans-serif" font-size="10" fill="#93C5FD" text-anchor="middle">Area Penyimpanan</text>

                <!-- Walkways -->
                <line x1="215" y1="50" x2="215" y2="450" stroke="#E2E8F0" stroke-width="2" stroke-dasharray="6,4"/>
                <line x1="430" y1="50" x2="430" y2="450" stroke="#E2E8F0" stroke-width="2" stroke-dasharray="6,4"/>
                <line x1="40" y1="160" x2="590" y2="160" stroke="#E2E8F0" stroke-width="2" stroke-dasharray="6,4"/>
                <line x1="770" y1="160" x2="765" y2="160" stroke="#E2E8F0" stroke-width="2" stroke-dasharray="6,4"/>
                <line x1="40"  y1="295" x2="765" y2="295" stroke="#E2E8F0" stroke-width="2" stroke-dasharray="6,4"/>

                <!-- Inventory points overlay -->
                <g t-foreach="state.points" t-as="point" t-key="point.id">
                    <g class="smi-inv-point"
                       t-att-class="{'smi-inv-point--selected': state.selectedId === point.id}"
                       t-on-click.stop="(ev) => this.onPointClick(point, ev)"
                       t-on-mouseenter="(ev) => this.onPointHover(point, ev)"
                       t-on-mouseleave.stop="() => this.onPointLeave()">
                        <circle
                            t-att-cx="point.x / 100 * 800"
                            t-att-cy="point.y / 100 * 500"
                            r="12"
                            t-att-fill="this.pointColor(point)"
                            stroke="white"
                            stroke-width="2"
                            opacity="0.92"/>
                        <text
                            t-att-x="point.x / 100 * 800"
                            t-att-y="point.y / 100 * 500 + 4"
                            font-family="Inter,system-ui,sans-serif"
                            font-size="8"
                            fill="white"
                            text-anchor="middle"
                            font-weight="600"
                            style="pointer-events:none;">
                            <t t-esc="point.name.substring(0, 4)"/>
                        </text>
                    </g>
                </g>

                <!-- Cursor preview dot in add_point mode -->
                <circle t-if="props.mode === 'add_point' and state.cursorPos"
                        t-att-cx="state.cursorPos.svgX"
                        t-att-cy="state.cursorPos.svgY"
                        r="10"
                        fill="#3B82F6"
                        opacity="0.5"
                        stroke="#1D4ED8"
                        stroke-width="2"
                        style="pointer-events:none;"/>
            </svg>

            <!-- Hover tooltip -->
            <div t-if="state.tooltip"
                 class="smi-map-tooltip"
                 t-att-style="'left:' + state.tooltip.x + 'px;top:' + state.tooltip.y + 'px'">
                <div class="smi-map-tooltip__title" t-esc="state.tooltip.point.name"/>
                <div t-foreach="state.tooltip.point.materials.slice(0, 4)" t-as="m" t-key="m.material_id"
                     class="smi-map-tooltip__row">
                    <span t-esc="m.material_name"/>
                    <span><t t-esc="m.jumlah_tersisa"/> <t t-esc="m.satuan"/></span>
                </div>
                <div t-if="state.tooltip.point.materials.length === 0"
                     style="font-size:12px;color:#94A3B8;">Tidak ada stok</div>
            </div>

            <!-- pick_output: "Ambil berapa?" input overlay -->
            <div t-if="props.mode === 'pick_output' and state.pickOutputPoint"
                 class="smi-map-panel">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                    <strong t-esc="state.pickOutputPoint.name"/>
                    <button class="smi-btn--icon" t-on-click="() => { state.pickOutputPoint = null; state.selectedId = null; }">✕</button>
                </div>
                <div t-foreach="state.pickOutputPoint.materials" t-as="m" t-key="m.material_id"
                     style="padding:8px 0;border-bottom:1px solid #E2E8F0;">
                    <div style="font-size:13px;font-weight:600;" t-esc="m.material_name"/>
                    <div style="font-size:12px;color:#64748B;margin-bottom:6px;">
                        Tersedia: <b t-esc="m.jumlah_tersisa"/> <t t-esc="m.satuan"/>
                    </div>
                    <input type="number"
                           class="smi-input"
                           style="font-size:13px;padding:6px 10px;"
                           placeholder="Ambil berapa?"
                           t-att-max="m.jumlah_tersisa"
                           min="0"
                           t-on-change="(ev) => this.onPickQtyChange(m, ev)"/>
                </div>
                <button class="smi-btn smi-btn--primary"
                        style="margin-top:12px;width:100%;"
                        t-on-click="confirmPickOutput">
                    Konfirmasi Pengambilan
                </button>
            </div>
        </div>
    `;

    static props = {
        mode: { type: String, optional: true },
        materialId: { type: Number, optional: true },
        onPointSelected: { type: Function, optional: true },
        onNewPoint: { type: Function, optional: true },
        onReady: { type: Function, optional: true },
    };

    static defaultProps = {
        mode: 'view',
    };

    setup() {
        this.svgEl = useRef("svgEl");
        this.state = useState({
            loading: true,
            points: [],
            selectedId: null,
            pickOutputPoint: null,
            pickQty: {},
            tooltip: null,
            cursorPos: null,
        });
        onWillStart(async () => {
            await this._loadPoints();
        });

        onMounted(() => {
            try {
                if (this.props.onReady && typeof this.props.onReady === 'function') {
                    this.props.onReady({ refresh: this.refresh.bind(this) });
                }
            } catch (e) {}
        });
    }

    async _loadPoints() {
        try {
            let url = '/smi/api/inventory_points';
            if (this.props.materialId) {
                url += `?material_id=${this.props.materialId}`;
            }
            const resp = await fetch(url, { credentials: 'same-origin' });
            if (resp.ok) {
                const data = await resp.json();
                this.state.points = data.points || [];
            }
        } catch (e) {
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    pointColor(point) {
        if (!point.materials || point.materials.length === 0) return '#94A3B8';
        const hasLow = point.materials.some(m => m.is_low_stock);
        if (hasLow) return '#F59E0B';
        return '#239670';
    }

    onPointHover(point, ev) {
        const x = ev.clientX + 12;
        const y = ev.clientY + 12;
        this.state.tooltip = { point, x, y };
    }

    onPointLeave() {
        this.state.tooltip = null;
    }

    onSvgMouseMove(ev) {
        if (this.props.mode !== 'add_point') return;
        const svg = this.svgEl.el;
        if (!svg) return;
        const rect = svg.getBoundingClientRect();
        const svgX = ((ev.clientX - rect.left) / rect.width) * 800;
        const svgY = ((ev.clientY - rect.top) / rect.height) * 500;
        this.state.cursorPos = { svgX, svgY };
    }

    onSvgMouseLeave() {
        this.state.cursorPos = null;
        this.state.tooltip = null;
    }

    async onPointClick(point, ev) {
        const mode = this.props.mode || 'view';

        if (mode === 'view') {
            this.state.selectedId = point.id;
            this.props.onPointSelected?.(point);

        } else if (mode === 'pick_input') {
            this.state.selectedId = point.id;
            this.props.onPointSelected?.(point);

        } else if (mode === 'pick_output') {
            const hasMaterial = point.materials && point.materials.length > 0;
            if (hasMaterial) {
                this.state.selectedId = point.id;
                this.state.pickOutputPoint = point;
                this.props.onPointSelected?.(point);
            }
        }
    }

    onSvgClick(ev) {
        if (this.props.mode !== 'add_point') return;
        const svg = this.svgEl.el;
        if (!svg) return;
        const rect = svg.getBoundingClientRect();
        const x = ((ev.clientX - rect.left) / rect.width) * 100;
        const y = ((ev.clientY - rect.top) / rect.height) * 100;
        this.props.onNewPoint?.({ x, y });
    }

    onPickQtyChange(material, ev) {
        const val = parseFloat(ev.target.value) || 0;
        this.state.pickQty = {
            ...this.state.pickQty,
            [material.material_id]: val,
        };
    }

    confirmPickOutput() {
        if (!this.state.pickOutputPoint) return;
        const picks = Object.entries(this.state.pickQty)
            .filter(([, qty]) => qty > 0)
            .map(([materialId, qty]) => ({
                materialId: parseInt(materialId),
                qty,
                pointId: this.state.pickOutputPoint.id,
                pointName: this.state.pickOutputPoint.name,
            }));
        this.props.onPointSelected?.({
            ...this.state.pickOutputPoint,
            picks,
        });
        this.state.pickOutputPoint = null;
        this.state.selectedId = null;
        this.state.pickQty = {};
    }

    /** Public: reload points from server (call after adding stock). */
    async refresh() {
        this.state.loading = true;
        await this._loadPoints();
    }
}
