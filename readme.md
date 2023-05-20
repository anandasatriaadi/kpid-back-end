# **KPID Jawa Timur Back End dengan Flask**

## **Instalasi**

Panduan ini memberikan instruksi tentang cara menginstal dan menjalankan KPID Jawa Timur Back End dengan Flask di mesin Linux. Silakan ikuti langkah-langkah berikut untuk mengatur dependensi yang diperlukan dan memulai server Flask.

## **Daftar Isi**
- [Instalasi Menggunakan Docker](#instalasi-menggunakan-docker-direkomendasikan)
  - [Instalasi Menggunakan Docker Compose](#instalasi-menggunakan-docker-composeyml-direkomendasikan)
  - [Instalasi Menggunakan Dockerfile](#instalasi-menggunakan-dockerfile)
    1. [Persiapan Volume dan Network](#persiapan-volume-dan-network)
    2. [Menjalankan Redis dari Docker Image](#menjalankan-redis-dari-docker-image)
    3. [Membangun dan Menjalankan Aplikasi](#membangun-dan-menjalankan-aplikasi)
- [Instalasi pada Sistem Linux](#instalasi-pada-sistem-linux)
  - [Persyaratan Sistem](#persyaratan-sistem)
  - [Intalasi Dependensi Sistem](#menginstal-dependensi-sistem)
  - [Persyaratan Sistem](#persyaratan-sistem)

## **MAndaTORY: Environment Variables**
Dalam menjalankan aplikasi diperlukan environment variables agar aplikasi dapat berjalan dengan baik. Berikut adalah tahapan setup Environment Variables:
1. Duplikat berkas `.env.example` menjadi `.env.dev.`

2. Isi variabel lingkungan yang diperlukan di berkas `.env.dev`.

## **Instalasi Menggunakan Docker (Direkomendasikan)**

Untuk menggunakan instalasi menggunakan Docker, pastikan Docker dan Docker Compose telah terpasang di sistem Anda. Ikuti langkah-langkah di bawah ini untuk instalasi Docker dan Docker Compose:

1. Instal Docker dengan mengikuti petunjuk resmi pada [Docker Installation Guide](https://docs.docker.com/get-docker/).

2. Instal Docker Compose dengan mengikuti petunjuk resmi pada [Docker Compose Installation Guide](https://docs.docker.com/compose/install/).

### **Instalasi Menggunakan docker-compose.yml (Direkomendasikan)**

Untuk menjalankan aplikasi menggunakan `docker-compose.yml`, lakukan langkah-langkah berikut:

1. Jalankan aplikasi menggunakan perintah berikut:

```bash
docker-compose up -d --build
```

Hal ini akan membangun dan menjalankan kontainer Docker yang diperlukan untuk KPID Jawa Timur Back End. Semua sudah dijalankan oleh Docker Compose, mulai dari server Redis, Redis worker, dan server Flask.

### **Instalasi Menggunakan Dockerfile**

Jika Anda ingin menggunakan Dockerfile untuk menjalankan aplikasi, lakukan langkah-langkah berikut:

#### **Persiapan Volume dan Network**
1. Buat Docker Volume, volume nanti akan digunakan untuk menyimpan data Redis. Jalankan perintah berikut:
```bash
docker volume create redis
```
Anda dapat mengganti nama volume dengan nama yang Anda inginkan.

2. Buat Docker Network, network nanti akan digunakan untuk menghubungkan Redis dengan aplikasi. Jalankan perintah berikut:
```bash
docker network create kpid-network
```
Anda dapat mengganti nama network dengan nama yang Anda inginkan.

#### **Menjalankan Redis dari Docker Image**
1. Jalankan Redis dari Docker Image resmi dengan menggunakan perintah berikut:
```bash
docker run -d \
  --name kpid-redis \
  --network kpid-network \
  -p 6379:6379 \
  -v redis:/data \
  --restart always \
  redis:7.0.10-alpine \
  redis-server --save 20 1 --loglevel warning --requirepass <password_redis_server>
```
Ganti `<password_redis_server>` dengan password yang ingin Anda gunakan pada Redis. 

Jika pada tahap sebelumnya Anda mengganti nama volume dan network, harap untuk mengganti nama volume dan network pada perintah di atas.

2. Pada `.env.dev` ganti nilai variabel `REDIS_HOST`
Pada tahap sebelumnya kita telah memberi nama container `kpid-redis`. Maka pada `.env.dev` dapat diganti menjadi berikut:
```bash
REDIS_HOST=kpid-redis
```
Jika Anda mengganti nama container, sesuaikan nama container tersebut.

#### **Membangun dan Menjalankan Aplikasi** 

1. Pastikan pada CLI Anda sedang berada pada direktori aplikasi sistem rekomendasi. Kompilasi dan build Image Docker menggunakan perintah berikut:

```bash
docker build -t kpid-back-end .
```

2. Setelah kompilasi selesai, jalankan Back End aplikasi menggunakan perintah berikut:

```bash
docker run -d \
  --name kpid-back-end \
  --network kpid-network \
  -p 5000:5000 \
  -v <direktori aplikasi>:/usr/src/app \
  --env-file .env.dev \
  kpid-back-end
```
Ganti `<direktori aplikasi>` dengan direktori aplikasi saat ini disimpan. Gunakan path absolut dikarenakan path relatif tidak dapat digunakan. 

Contoh:
```bash
docker run -d \
  --name kpid-back-end \
  --network kpid-network \
  -p 5000:5000 \
  -v /home/annd/kpid-back-end:/usr/src/app \
  --env-file .env.dev \
  kpid-back-end
```

Catatan: Jika pada tahap sebelumnya Anda mengganti nama network, harap untuk mengganti nama network pada perintah di atas.

3. Jalankan Redis Worker menggunakan perintah berikut:

```bash
docker run -d \
  --name kpid-redis-worker \
  --network kpid-network \
  --env-file .env.dev \
  kpid-back-end \
  python3 redis_worker.py
```

Catatan: Jika pada tahap sebelumnya Anda mengganti nama network, harap untuk mengganti nama network pada perintah di atas.

## **Instalasi pada Sistem Linux**

### **Persyaratan Sistem**

Sebelum melanjutkan dengan instalasi, pastikan sistem Anda memenuhi persyaratan berikut:

- FFMPEG
- WKHTMLTOPDF
- Protocol Buffers (protobuf)
- Redis

### **Menginstal Dependensi Sistem**

#### **FFMPEG**

```bash
sudo apt update
sudo apt install -y ffmpeg
```

Untuk sistem operasi lain, dapat menggunakan tautan berikut untuk panduan instalasi [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)

#### **WKHTMLTOPDF**

**Catatan:**  
Pastikan sistem Ubuntu sudah terinstall `wget`

**Ubuntu 22.04**

```bash
wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
sudo apt install -f ./wkhtmltox_0.12.6.1-2.jammy_amd64.deb
```

**Ubuntu 20.04**

```bash
wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1.focal_amd64.deb
sudo apt install -f ./wkhtmltox_0.12.6.1.focal_amd64.deb
```

Untuk sistem operasi lain, dapat menggunakan tautan berikut untuk instalasi [https://wkhtmltopdf.org/downloads.html](https://wkhtmltopdf.org/downloads.html)

#### **Protocol Buffers (protobuf)**
Protobuf diperlukan dalam penggunaan model dari Tensorflow. Berikut adalah perintah yang dapat dijalankan untuk menginstal protobuf pada sistem Ubuntu:
```bash
sudo apt install -y protobuf-compiler
```

Untuk operasi sistem lainnya dapat mengunduhnya melalui tautan ini [https://developers.google.com/protocol-buffers/docs/downloads](https://developers.google.com/protocol-buffers/docs/downloads)

#### **Redis**
```bash
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list

sudo apt-get update
sudo apt-get install redis
```

Untuk sistem operasi lain, dapat menggunakan tautan berikut untuk instalasi [https://redis.io/docs/getting-started/installation/](https://redis.io/docs/getting-started/installation/)

Setelah instalasi diharapkan mensetting password untuk akses ke Redis server. Password dari Redis server dapat diatur dengan perintah berikut:
```bash
redis-cli config set requirepass <password_redis_server>
```
Ganti `<password_redis_server>` dengan password yang ingin Anda gunakan pada Redis. Redis server sudah berhasil diunduh dan dijalankan.

### **Instalasi Dependensi Python dan Menjalankan Server**
#### **1. Membuat Lingkungan Virtual**

Untuk membuat lingkungan virtual, buka terminal Anda dan jalankan perintah berikut:

```bash
python3 -m venv ./env
```


#### **2. Mengaktifkan Lingkungan Virtual**

Aktifkan lingkungan virtual dengan menjalankan perintah berikut:

```bash
source ./env/bin/activate
```


#### **3. Menginstal Dependensi**

Pasang paket Python yang diperlukan dengan menjalankan perintah berikut:

```bash
pip install -r ./requirements.txt
```

Ini akan menginstal semua dependensi Python yang diperlukan untuk KPID Jawa Timur Back End.

#### **4. Menjalankan Redis Worker**

Untuk memulai Redis Worker, jalankan perintah berikut:

```bash
python ./redis-worker.py
```

#### **5. Menjalankan Server Flask**

Kemudian pada CLI yang berbeda yang sudah diaktifkan lingkungan virtual, untuk memulai server Flask jalankan perintah berikut:

```bash
gunicorn --bind 0.0.0.0:5000 --timeout=0 --workers=2 --access-logfile '-' run:app
```

Server sekarang sudah berjalan, siap untuk menangani permintaan dari sistem Front End KPID Jawa Timur.
