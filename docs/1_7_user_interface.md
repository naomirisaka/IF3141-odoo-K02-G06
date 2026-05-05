# I.7 User Interface

> **Catatan:** Semua tampilan layar menggunakan **opsi 2 — Screenshot langsung dari Odoo**.
> Placeholder `[SS: <url>]` menandakan halaman yang perlu di-screenshot.
> Login terlebih dahulu dengan akun yang sesuai sebelum mengambil screenshot.

---

## I.7.1 Screen Mockup

---

### Tabel 1.8.1 Screen Mockup — Halaman Login

| | |
|---|---|
| **Nama Layar** | Halaman Login |
| **Deskripsi Layar** | Layar autentikasi yang digunakan semua pengguna untuk masuk ke sistem dengan memasukkan username dan password. Menampilkan pesan error jika kredensial salah dan pesan akun terkunci jika gagal 5 kali. |
| **User** | Admin, Kepala Produksi, Staf Produksi, Direktur |
| **Tampilan Layar** | **[SS: http://localhost:8069/web/login]** |

---

### Tabel 1.8.2 Screen Mockup — Dashboard / Beranda

| | |
|---|---|
| **Nama Layar** | Dashboard / Beranda |
| **Deskripsi Layar** | Layar utama setelah login. Menampilkan ringkasan inventaris: jumlah total bahan, total stok, pesanan aktif, jumlah bahan stok rendah, daftar 5 bahan dengan stok terkritis, pesanan terbaru, log aktivitas terbaru, dan peta denah mini. |
| **User** | Admin, Kepala Produksi, Staf Produksi, Direktur |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/dashboard]** — login sebagai `kepala` untuk tampilan lengkap |

---

### Tabel 1.8.3 Screen Mockup — Daftar Bahan Baku (Stok)

| | |
|---|---|
| **Nama Layar** | Daftar Bahan Baku |
| **Deskripsi Layar** | Layar yang menampilkan seluruh daftar bahan baku beserta total stok, satuan, kategori, status stok rendah, dan tanggal terakhir ditambahkan. Dapat digunakan untuk navigasi ke detail bahan. |
| **User** | Admin, Kepala Produksi, Staf Produksi, Direktur |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/stok]** |

---

### Tabel 1.8.4 Screen Mockup — Detail Bahan Baku

| | |
|---|---|
| **Nama Layar** | Detail Bahan Baku |
| **Deskripsi Layar** | Layar yang menampilkan informasi lengkap satu bahan baku: nama, kategori, satuan, warna/varian, total stok, stok minimum (reorder point), status stok rendah, dan riwayat stok masuk per lokasi. Kepala Produksi dapat mengedit nilai stok minimum di layar ini. |
| **User** | Admin, Kepala Produksi, Staf Produksi, Direktur |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/stok/\<id\>]** — buka salah satu bahan dari daftar stok |

--- 

### Tabel 1.8.5 Screen Mockup — Form Tambah Stok

| | |
|---|---|
| **Nama Layar** | Form Tambah Stok (Penerimaan Bahan Baku) |
| **Deskripsi Layar** | Formulir penerimaan stok baru. Pengguna memilih bahan baku, memasukkan jumlah, memilih titik lokasi inventori dari denah, dan menambahkan catatan. Sistem otomatis mencatat timestamp dan identitas penginput. |
| **User** | Admin, Kepala Produksi, Staf Produksi |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/stok/tambah]** |

---

### Tabel 1.8.6 Screen Mockup — Visualisasi Denah Interaktif

| | |
|---|---|
| **Nama Layar** | Visualisasi Denah Interaktif |
| **Deskripsi Layar** | Layar denah area produksi yang menampilkan titik-titik inventori dengan warna berbeda sesuai status stok (hijau = normal, kuning = sebagian rendah, merah = semua rendah, abu-abu = kosong). Pengguna dapat mengklik titik untuk melihat detail stok. Kepala Produksi dapat menambah titik baru. |
| **User** | Admin, Kepala Produksi, Staf Produksi, Direktur |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/stok/denah]** |

---

### Tabel 1.8.7 Screen Mockup — Daftar Pesanan (Order)

| | |
|---|---|
| **Nama Layar** | Daftar Pesanan |
| **Deskripsi Layar** | Layar yang menampilkan seluruh daftar pesanan produksi beserta nama pesanan, nomor SPK, tanggal, status (draft/dikonfirmasi/selesai/dibatalkan), dan user pembuat. |
| **User** | Admin, Kepala Produksi, Staf Produksi |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/order]** |

---

### Tabel 1.8.8 Screen Mockup — Form Tambah Pesanan Step 1

| | |
|---|---|
| **Nama Layar** | Form Tambah Pesanan — Step 1 (Info Pesanan) |
| **Deskripsi Layar** | Langkah pertama pencatatan pesanan. Pengguna memasukkan nama pesanan dan nomor SPK. |
| **User** | Kepala Produksi, Staf Produksi |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/order/tambah]** |

---

### Tabel 1.8.9 Screen Mockup — Form Tambah Pesanan Step 2

| | |
|---|---|
| **Nama Layar** | Form Tambah Pesanan — Step 2 (Rincian Material) |
| **Deskripsi Layar** | Langkah kedua pencatatan pesanan. Pengguna menambahkan daftar bahan baku yang dibutuhkan beserta kuantitasnya. Sistem menampilkan indikator real-time "Stok Cukup" (hijau) atau "Stok Tidak Cukup" (merah) untuk setiap bahan yang diinput. |
| **User** | Kepala Produksi, Staf Produksi |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/order/tambah/step2]** — setelah mengisi step 1 |

---

### Tabel 1.8.10 Screen Mockup — Form Tambah Pesanan Step 3 (Konfirmasi & Pilih Metode)

| | |
|---|---|
| **Nama Layar** | Form Tambah Pesanan — Step 3 (Konfirmasi & Metode Pengurangan Stok) |
| **Deskripsi Layar** | Langkah terakhir sebelum konfirmasi order. Pengguna memilih metode pengurangan stok: **Otomatis (FIFO)** — sistem memotong stok dari batch tertua, atau **Manual** — pengguna memilih lokasi fisik spesifik dari denah. Setelah konfirmasi, stok berkurang dan order masuk status "Dikonfirmasi". |
| **User** | Kepala Produksi, Staf Produksi |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/order/tambah/step3]** — setelah mengisi step 2 |

---

### Tabel 1.8.11 Screen Mockup — Detail Pesanan

| | |
|---|---|
| **Nama Layar** | Detail Pesanan |
| **Deskripsi Layar** | Layar yang menampilkan rincian lengkap satu pesanan: header (nama, SPK, tanggal, status), daftar bahan yang digunakan beserta kuantitas dan metode pemotongan, dan tombol aksi (batalkan order jika masih draft). |
| **User** | Admin, Kepala Produksi, Staf Produksi |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/order/\<id\>]** — buka salah satu order dari daftar |

--- 

### Tabel 1.8.12 Screen Mockup — Log Aktivitas

| | |
|---|---|
| **Nama Layar** | Log Aktivitas |
| **Deskripsi Layar** | Layar audit trail yang mencatat seluruh aktivitas pengguna dalam sistem: tambah stok, konfirmasi order, dll. Menampilkan nama pengguna, jabatan, tanggal, tipe aktivitas, dan deskripsi. |
| **User** | Admin, Kepala Produksi, Direktur |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/activity]** |

---

### Tabel 1.8.13 Screen Mockup — Manajemen Pengguna

| | |
|---|---|
| **Nama Layar** | Manajemen Pengguna |
| **Deskripsi Layar** | Layar khusus Admin untuk melihat daftar seluruh pengguna sistem beserta peran (role) masing-masing. Digunakan untuk menambah, memperbarui, atau menonaktifkan akun pengguna. |
| **User** |    Admin |
| **Tampilan Layar** | **[SS: http://localhost:8069/smi/pengguna]** — login sebagai `admin_smi` |

---

## I.7.2 Pemetaan Layar

**Tabel 1.8.2 Tabel Pemetaan Layar**

| No | Use Case / Activity | Layar |
|---|---|---|
| UC-01 | Melakukan Login | A. Halaman Login (`/web/login`) |
| UC-02 | Mengelola Akun Pengguna | A. Halaman Manajemen Pengguna (`/smi/pengguna`) |
| UC-03 | Mencatat Penerimaan Stok Baru | A. Form Tambah Stok (`/smi/stok/tambah`) <br> B. Visualisasi Denah — pemilihan titik lokasi (`/smi/stok/denah`) |
| UC-04 | Mencatat Rincian Pesanan | A. Form Tambah Pesanan Step 1 — Info Pesanan (`/smi/order/tambah`) <br> B. Form Tambah Pesanan Step 2 — Rincian Material (`/smi/order/tambah/step2`) |
| UC-05 | Mengurangi Stok Otomatis (FIFO) | A. Form Tambah Pesanan Step 3 — Konfirmasi & Pilih Mode Auto (`/smi/order/tambah/step3`) <br> B. Detail Pesanan — hasil konfirmasi (`/smi/order/<id>`) |
| UC-06 | Mengurangi Stok Manual | A. Form Tambah Pesanan Step 3 — Konfirmasi & Pilih Mode Manual (`/smi/order/tambah/step3`) <br> B. Detail Pesanan — hasil konfirmasi (`/smi/order/<id>`) |
| UC-07 | Melihat Visualisasi Denah | A. Visualisasi Denah Interaktif (`/smi/stok/denah`) |
| UC-08 | Mengelola Titik Lokasi Inventori | A. Visualisasi Denah Interaktif — mode tambah titik (`/smi/stok/denah`) |
| UC-09 | Konfigurasi Stok Minimum | A. Detail Bahan Baku — edit stok minimum (`/smi/stok/<id>`) |
| UC-10 | Memantau Laporan Stok Real-Time | A. Dashboard / Beranda (`/smi/dashboard`) <br> B. Daftar Bahan Baku (`/smi/stok`) |
| UC-11 | Mencetak Laporan Stok | A. Dashboard / Beranda — fitur export (`/smi/dashboard`) |

---

## Panduan Screenshot

Berikut daftar screenshot yang perlu diambil secara berurutan:

| # | URL | Login sebagai | Keterangan |
|---|---|---|---|
| 1 | `http://localhost:8069/web/login` | — (belum login) | Tampilan form login kosong |
| 2 | `http://localhost:8069/smi/dashboard` | `kepala` / `kepala123` | Dashboard penuh dengan data |
| 3 | `http://localhost:8069/smi/stok` | `kepala` | Daftar seluruh bahan baku |
| 4 | `http://localhost:8069/smi/stok/<id>` | `kepala` | Buka salah satu bahan dari daftar |
| 5 | `http://localhost:8069/smi/stok/tambah` | `staf1` / `staf123` | Form tambah stok (kosong) |
| 6 | `http://localhost:8069/smi/stok/denah` | `staf1` | Denah dengan titik-titik berwarna |
| 7 | `http://localhost:8069/smi/order` | `staf1` | Daftar pesanan |
| 8 | `http://localhost:8069/smi/order/tambah` | `staf1` | Step 1 form order |
| 9 | `http://localhost:8069/smi/order/tambah/step2` | `staf1` | Step 2 setelah isi step 1 |
| 10 | `http://localhost:8069/smi/order/tambah/step3` | `staf1` | Step 3 setelah isi step 2 |
| 11 | `http://localhost:8069/smi/order/<id>` | `staf1` | Buka salah satu order dari daftar |
| 12 | `http://localhost:8069/smi/activity` | `kepala` | Log aktivitas |
| 13 | `http://localhost:8069/smi/pengguna` | `admin_smi` / `admin123` | Halaman manajemen pengguna |
