# IF3141 Sistem Informasi — Sistem Manajemen Inventaris (SMI)

> Tugas Besar IF3141 Sistem Informasi — K02 Kelompok 06

## Daftar Isi

- [Gambaran Umum](#gambaran-umum)
- [Fitur Utama](#fitur-utama)
- [Teknologi](#teknologi)
- [Struktur Direktori](#struktur-direktori)
- [Pre-requisites](#pre-requisites)
- [Cara Menjalankan Aplikasi](#cara-menjalankan-aplikasi)
- [Akun Demo](#akun-demo)
- [Hak Akses Per Peran](#hak-akses-per-peran)
- [Panduan Penggunaan Fitur](#panduan-penggunaan-fitur)
- [Pengembangan Modul](#pengembangan-modul)
- [Database Migration](#database-migration)
- [Menjalankan Tests](#menjalankan-tests)

---

## Gambaran Umum

**Sistem Manajemen Inventaris (SMI)** adalah modul kustom Odoo 17.0 yang dirancang untuk manajemen bahan baku pada CV Dunia Offset Printing. Sistem ini dibangun di atas platform Odoo dan menyediakan antarmuka web berbahasa Indonesia untuk pengelolaan stok, pemrosesan order produksi, serta pelaporan aktivitas gudang.

Sistem ini memungkinkan pelacakan stok bahan baku secara real-time, pengambilan stok berbasis FIFO (*First-In-First-Out*), notifikasi otomatis stok minimum, serta audit trail seluruh aktivitas pengguna.

---

## Fitur Utama

### Manajemen Bahan & Stok
- Pencatatan bahan baku beserta kategori dan satuan (UOM)
- Penambahan stok masuk dengan pencatatan lokasi gudang
- Pelacakan stok berbasis batch FIFO (setiap penerimaan stok dicatat sebagai batch tersendiri)
- Status stok per batch: **Tersedia** / **Habis**
- Perhitungan total stok otomatis per material
- Notifikasi stok minimum melalui email dan real-time bus notification

### Manajemen Order
- Form order multi-langkah (3 tahap: header → rincian material → konfirmasi)
- Dua mode pengambilan stok:
  - **Auto (FIFO):** sistem otomatis mengambil dari batch stok terlama
  - **Manual:** pengguna memilih sendiri batch dan jumlah yang diambil
- Pratinjau kalkulasi FIFO sebelum konfirmasi
- State machine order: `Draft` → `Dikonfirmasi` → `Selesai` / `Dibatalkan`
- Validasi ketersediaan stok sebelum konfirmasi order

### Dashboard
- Ringkasan stok: total material, material di bawah minimum, nilai stok
- Material dengan stok terbanyak
- Order terbaru
- Feed aktivitas terkini
- Peta denah gudang interaktif (kode warna berdasarkan status stok)

### Denah Gudang (Map Widget)
- Visualisasi titik penyimpanan bahan pada denah gudang
- Kode warna titik penyimpanan:
  - **Hijau:** semua stok di atas batas minimum
  - **Oranye:** sebagian stok di bawah minimum
  - **Merah:** semua stok di bawah minimum
  - **Abu-abu:** tidak ada stok

### Log Aktivitas
- Pencatatan otomatis seluruh aktivitas: stok masuk/keluar, order dibuat/selesai/dibatalkan, penambahan titik gudang, penambahan pengguna
- Informasi peran/jabatan pengguna pada setiap log
- Tautan ke rekaman terkait

### Keamanan & Manajemen Pengguna
- Kunci akun otomatis setelah **5 kali gagal login** (durasi kunci: 10 menit)
- Kebijakan perubahan password setiap **90 hari**
- Kontrol akses berbasis peran (4 grup)
- Tampilan menu disesuaikan per peran

---

## Teknologi

| Komponen | Teknologi |
|----------|-----------|
| Platform | Odoo 17.0 |
| Backend | Python 3.11, ORM Odoo |
| Frontend | QWeb Templates, JavaScript (ES6), CSS |
| Database | PostgreSQL 16 |
| Infrastruktur | Docker, Docker Compose |
| Notifikasi | Odoo Bus (WebSocket), Email SMTP |

---

## Struktur Direktori

```
IF3141-odoo-K02-G06/
├── config/
│   └── odoo.conf                   # Konfigurasi Odoo (port, DB, addons path)
├── custom_addons/
│   └── inventory_smi/              # Modul kustom utama
│       ├── __manifest__.py         # Metadata modul (nama, versi, dependensi)
│       ├── controllers/            # Route & logika HTTP
│       │   ├── main.py             # Dashboard & index
│       │   ├── auth.py             # Login, logout, ganti password
│       │   ├── stock_controller.py # Stok: list, tambah, detail
│       │   ├── order_controller.py # Order: list, form 3-step, detail
│       │   ├── activity_controller.py # Log aktivitas
│       │   ├── user_controller.py  # Manajemen pengguna
│       │   └── api.py              # JSON API endpoints
│       ├── models/                 # Model database (ORM)
│       │   ├── material.py         # smi.material, smi.material.category, smi.uom
│       │   ├── stock_entry.py      # smi.stock_entry (batch stok FIFO)
│       │   ├── inventory_point.py  # smi.inventory_point (titik penyimpanan)
│       │   ├── order.py            # smi.order, smi.order.line, smi.order.pick
│       │   ├── activity_log.py     # smi.activity.log & notifikasi
│       │   └── res_users_extend.py # Ekstensi res.users (lockout, password policy)
│       ├── views/                  # Template XML (QWeb)
│       │   ├── layout_template.xml # Layout utama dengan sidebar navigasi
│       │   ├── auth_templates.xml  # Halaman login & ganti password
│       │   ├── dashboard_views.xml # Dashboard
│       │   ├── material_views.xml  # Daftar material (Odoo backend view)
│       │   ├── stock_*.xml         # Halaman stok (list, form, detail)
│       │   ├── order_*.xml         # Halaman order (list, form step 1-3, detail)
│       │   ├── denah_template.xml  # Peta denah gudang
│       │   ├── activity_template.xml # Log aktivitas
│       │   └── pengguna_template.xml # Manajemen pengguna
│       ├── data/
│       │   ├── demo_users.xml      # Akun demo (4 peran)
│       │   ├── email_templates.xml # Template email notifikasi stok minimum
│       │   └── seed_materials.xml  # Data awal bahan baku
│       ├── security/
│       │   ├── smi_security.xml    # Definisi grup/peran
│       │   └── ir.model.access.csv # Aturan akses per model per grup
│       ├── static/src/
│       │   ├── css/smi_theme.css   # Tema kustom antarmuka
│       │   ├── js/components/MapWidget.js # Widget peta gudang
│       │   └── img/denah.svg       # Denah lantai gudang
│       └── tests/                  # Test suite
├── scripts/
│   ├── export_db.sh / export_db.cmd  # Export database & filestore
│   └── import_db.sh / import_db.cmd  # Import database & filestore
├── dump/                           # Folder penyimpanan file dump database
├── docs/                           # Dokumentasi tambahan
├── docker-compose.yml              # Orkestrasi Docker (Odoo + PostgreSQL)
├── requirements.txt                # Dependensi Python
└── README.md
```

---

## Pre-requisites

Pastikan perangkat lunak berikut sudah terpasang sebelum memulai:

1. **Docker Desktop**
   - Download: https://www.docker.com/products/docker-desktop/
   - Pastikan Docker Engine berjalan sebelum menjalankan perintah docker

2. **Python 3.11** (untuk pengembangan lokal)
   - Digunakan untuk membuat virtual environment pengembangan modul
   - Download: https://www.python.org/downloads/release/python-3110/

---

## Cara Menjalankan Aplikasi

### 1. Clone Repository

```bash
git clone <url-repository>
cd IF3141-odoo-K02-G06
```

### 2. Jalankan Docker Services

```bash
docker compose build --pull --no-cache web
docker compose up -d
```

Perintah ini menjalankan dua service:
- **web**: Odoo 17.0 pada port `8069`
- **db**: PostgreSQL 16 pada port `5432` (internal)

Tunggu beberapa saat hingga Odoo selesai inisialisasi (biasanya 30–60 detik saat pertama kali).

### 3. Buka Aplikasi di Browser

```
http://localhost:8069
```

### 4. Login

Gunakan salah satu akun berikut (lihat [Akun Demo](#akun-demo)).

Untuk login sebagai administrator Odoo (akses penuh ke backend Odoo):
- **Username:** `admin`
- **Password:** `admin`

### 5. Akses Modul SMI

Setelah login, navigasi ke:

```
http://localhost:8069/smi
```

Atau klik menu **SMI** pada aplikasi Odoo.

### 6. Aktifkan Developer Mode (opsional, untuk pengembangan)

- Masuk ke **Settings → General Settings**
- Scroll ke bawah dan nyalakan **Developer Mode / Developer Access**
- Atau akses langsung: `http://localhost:8069/web?debug=1`

### 7. Menghentikan Aplikasi

```bash
docker compose down
```

---

## Akun Demo

Modul menyediakan 4 akun demo yang sesuai dengan peran dalam sistem:

| Nama | Username | Password | Peran |
|------|----------|----------|-------|
| Admin SMI | `admin_smi` | `admin123` | Admin |
| Kepala Produksi | `kepala` | `kepala123` | Kepala Produksi |
| Staf Produksi | `staf1` | `staf123` | Staf Produksi |
| Direktur | `direktur` | `direktur123` | Direktur |

> **Catatan:** Akun admin Odoo bawaan (`admin` / `admin`) memiliki akses ke seluruh backend Odoo, tetapi berbeda dengan grup SMI di atas.

---

## Hak Akses Per Peran

| Fitur | Admin | Kepala Produksi | Staf Produksi | Direktur |
|-------|:-----:|:---------------:|:-------------:|:--------:|
| Dashboard | ✅ | ✅ | ✅ | ✅ |
| Lihat Stok | ✅ | ✅ | ✅ | ✅ |
| Tambah Stok | ✅ | ✅ | ✅ | ❌ |
| Hapus Stok | ✅ | ❌ | ❌ | ❌ |
| Lihat Order | ✅ | ✅ | ✅ | ✅ |
| Buat Order | ✅ | ✅ | ✅ | ❌ |
| Konfirmasi Order | ✅ | ✅ | ✅ | ❌ |
| Batalkan Order | ✅ | ✅ | ✅ | ❌ |
| Hapus Order | ✅ | ❌ | ❌ | ❌ |
| Kelola Material | ✅ | ✅ | ❌ | ❌ |
| Kelola Titik Gudang | ✅ | ✅ | ❌ | ❌ |
| Log Aktivitas | ✅ | ✅ (read) | ✅ (read) | ✅ (read) |
| Manajemen Pengguna | ✅ | ❌ | ❌ | ❌ |

---

## Panduan Penggunaan Fitur

### Dashboard (`/smi/dashboard`)

Halaman utama setelah login. Menampilkan:
- Statistik stok (total material, stok di bawah minimum, total unit)
- Material dengan jumlah stok terbesar
- Order produksi terbaru
- Feed aktivitas terkini
- Denah gudang interaktif

### Manajemen Stok (`/smi/stok`)

**Melihat Daftar Stok:**
- Klik menu **Stok** di sidebar
- Gunakan kolom pencarian untuk mencari berdasarkan nama material
- Klik header kolom untuk sorting

**Menambah Stok:**
1. Klik tombol **+ Tambah Stok**
2. Pilih material, lokasi gudang, masukkan jumlah dan tanggal masuk
3. Tambahkan catatan (opsional)
4. Klik **Simpan**

**Detail Stok:**
- Klik baris material untuk melihat riwayat stok per batch

### Manajemen Order (`/smi/order`)

**Membuat Order Baru (3 Langkah):**

**Langkah 1 — Header Order:**
- Masukkan nama order, nomor SPK, tanggal, dan catatan
- Klik **Lanjutkan**

**Langkah 2 — Rincian Material:**
- Tambahkan baris material yang dibutuhkan
- Masukkan jumlah kebutuhan per material
- Pilih mode pengambilan:
  - **Auto:** sistem otomatis pilih batch FIFO terlama
  - **Manual:** pilih sendiri batch stok dan jumlah yang diambil
- Klik **Lanjutkan ke Konfirmasi**

**Langkah 3 — Konfirmasi:**
- Review ringkasan order dan rencana pengambilan stok
- Klik **Konfirmasi Order** untuk memproses (stok langsung dikurangi)

**Menyelesaikan / Membatalkan Order:**
- Buka halaman detail order
- Klik **Selesaikan** atau **Batalkan**

### Denah Gudang (`/smi/denah`)

- Titik penyimpanan ditampilkan pada denah lantai gudang
- Warna titik menunjukkan status stok di lokasi tersebut
- Hover pada titik untuk melihat detail material dan stok

### Log Aktivitas (`/smi/aktivitas`)

- Menampilkan riwayat seluruh aktivitas sistem secara kronologis
- Setiap entri mencatat: pengguna, jabatan, waktu, tipe aksi, dan deskripsi

---

## Pengembangan Modul

### Setup Virtual Environment

```bash
python3.11 -m venv .venv

# Linux/macOS:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Menambahkan Modul ke Odoo

Setelah membuat atau mengubah modul di `custom_addons/`:

1. Masuk ke menu **Apps**
2. Klik **Update Apps List**
3. Cari modul baru dan klik **Install**

### Memperbarui Modul yang Sudah Terpasang

Jika mengubah model (perubahan database):

```bash
docker compose exec web odoo -u inventory_smi -d postgres
```

Atau restart container:

```bash
docker compose restart web
```

### Struktur Modul Kustom

File utama yang perlu diperhatikan saat pengembangan:

```
inventory_smi/
├── __manifest__.py     # Tambahkan file baru ke daftar 'data', 'assets'
├── models/             # Definisi model (tambah field, method)
├── controllers/        # Route HTTP baru
├── views/              # Template QWeb baru
└── security/
    └── ir.model.access.csv   # Aturan akses untuk model baru
```

---

## Database Migration

Karena Odoo menggunakan database lokal, diperlukan proses export/import untuk berbagi perubahan database antar anggota tim.

### Sebelum Export/Import

Matikan seluruh service terlebih dahulu:

```bash
docker compose down
```

### Export Database

Gunakan saat ingin membagikan perubahan database ke anggota tim lain.

- **macOS/Linux:**
  ```bash
  ./scripts/export_db.sh
  ```

- **Windows:**
  ```bat
  scripts\export_db.cmd
  ```

Hasil export tersimpan di folder `dump/` dengan format:
- `dump/odoo_backup_TIMESTAMP.dump` — snapshot database
- `dump/odoo_backup_TIMESTAMP_filestore.tar.gz` — filestore (attachment, gambar, dll.)

### Import Database

Gunakan saat menerima perubahan database dari rekan tim (setelah `git pull`).

- **macOS/Linux:**
  ```bash
  ./scripts/import_db.sh
  ```

- **Windows:**
  ```bat
  scripts\import_db.cmd
  ```

Proses import akan:
1. Menghentikan container web
2. Menghapus dan membuat ulang database
3. Merestore database dari file dump terbaru
4. Merestore filestore
5. Menjalankan upgrade modul `inventory_smi`
6. Menghidupkan kembali container web

> **Perhatian:** Proses import akan **menghapus** seluruh data database lokal yang ada. Pastikan sudah melakukan export jika ada data lokal yang ingin disimpan.

---

## Menjalankan Tests

Test suite tersedia di `custom_addons/inventory_smi/tests/`. Untuk menjalankan:

```bash
docker compose exec web python -m pytest custom_addons/inventory_smi/tests/
```

Atau menggunakan Odoo test runner:

```bash
docker compose exec web odoo --test-enable -u inventory_smi -d postgres
```

### Cakupan Test

| File Test | Cakupan |
|-----------|---------|
| `test_models.py` | CRUD model, validasi constraint |
| `test_stock.py` | Penambahan stok, state management |
| `test_order.py` | Alur order, algoritma FIFO |
| `test_auth.py` | Login lockout, kebijakan password |
| `test_access_control.py` | Validasi hak akses per peran |
| `test_activity_notif.py` | Trigger notifikasi stok minimum |
| `test_dashboard.py` | Agregasi data dashboard |
| `test_stock_ui.py` | Template & route stok |
| `test_order_ui.py` | Template & route order |
| `test_activity_ui.py` | Template log aktivitas |
| `test_map_api.py` | API endpoint peta gudang |

---

## Troubleshooting

**Container tidak mau start:**
```bash
docker compose logs web
docker compose logs db
```

**Modul tidak muncul di Apps:**
- Pastikan folder modul ada di `custom_addons/`
- Periksa `__manifest__.py` tidak ada syntax error
- Lakukan **Update Apps List** dari menu Apps

**Perubahan model tidak terupdate:**
```bash
docker compose restart web
# atau force upgrade:
docker compose exec web odoo -u inventory_smi -d postgres
```

**Port 8069 sudah dipakai:**
- Ubah mapping port di `docker-compose.yml`: `"8080:8069"` lalu akses via `localhost:8080`
