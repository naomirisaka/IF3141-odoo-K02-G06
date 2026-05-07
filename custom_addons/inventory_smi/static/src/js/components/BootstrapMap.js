/** @odoo-module **/
import { mount, whenReady } from "@odoo/owl";
import { templates } from "@web/core/assets";
import { MapWidget } from "@inventory_smi/js/components/MapWidget";

whenReady(() => {
    const target = document.getElementById('smi_map_root');
    if (target) {
        mount(MapWidget, target, {
            templates,
            props: {
                mode: 'view',
                onNewPoint: async (coords) => {
                    // 1. Ask for the required 'name' field
                    const name = prompt("Masukkan Nama Titik Penyimpanan:");
                    if (!name) return;

                    // 2. Prepare the data
                    const payload = {
                        name: name,
                        koordinat_x: coords.x, // Already 0-100 from MapWidget
                        koordinat_y: coords.y,
                        deskripsi: `Ditambahkan via peta pada ${new Date().toLocaleString()}`
                    };

                    // 3. Send to your Python Controller
                    try {
                        // Using FormData because your route likely expects it or use JSON if route is type='json'
                        const formData = new FormData();
                        for (const key in payload) {
                            formData.append(key, payload[key]);
                        }

                        const response = await fetch('/smi/api/inventory_points', {
                            method: 'POST',
                            body: formData,
                        });

                        if (response.ok) {
                            const result = await response.json();
                            console.log("Success:", result);
                            // Refresh the page to show the new dot (rendered by the model)
                            window.location.reload();
                        } else {
                            const err = await response.json();
                            alert("Gagal menambahkan titik: " + (err.error || "Unknown Error"));
                        }
                    } catch (error) {
                        console.error("Network Error:", error);
                        alert("Koneksi gagal. Pastikan server Odoo berjalan.");
                    }
                },
                onPointSelected: (point) => {
            // Call the global function sitting in your XML script tag
            if (window.showPointPanel) {
                window.showPointPanel(point.id);
            }
        },
            }
        });
    }
});