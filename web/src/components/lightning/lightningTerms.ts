export const EVENT_TYPE_INFO: Record<string, string> = {
  lightning:
    "Sambaran petir asli yang terdeteksi sensor, lengkap dengan estimasi jarak dan energi.",
  disturber:
    "Interferensi buatan manusia (lampu, motor listrik, charger, microwave) yang mirip petir tetapi dikenali sensor sebagai bukan petir.",
  noise:
    "Derau latar elektromagnetik yang terlalu tinggi di sekitar sensor, sehingga mengganggu deteksi.",
};

export const LIGHTNING_STATUS_INFO: Record<string, string> = {
  quiet: "Tidak ada aktivitas petir terdeteksi pada menit ini.",
  noise: "Tingkat derau latar tinggi pada menit ini.",
  disturber: "Banyak interferensi buatan manusia terdeteksi pada menit ini.",
  activity: "Ada sambaran petir nyata terdeteksi pada menit ini.",
  saturated: "Aktivitas sangat tinggi hingga sensor mengalami saturasi.",
  no_data: "Belum ada data untuk menit ini.",
};
