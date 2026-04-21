import minecraft_launcher_lib
import subprocess
import os
import sys
import json
from pick import pick
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich import print as rprint

# Inisialisasi Console UI
console = Console()

# ==========================================
# KONFIGURASI BACKEND & DIREKTORI
# ==========================================
HOME = os.path.expanduser("~")
LAUNCHER_DIR = os.path.join(HOME, ".cihuy_launcher")
MC_DIR = os.path.join(LAUNCHER_DIR, "minecraft_data")
CONFIG_FILE = os.path.join(LAUNCHER_DIR, "config.json")

# Mapping Java Otomatis (Standar Linux Path)
# Minecraft beda versi, beda kebutuhan Java.
JAVA_PATHS = {
    "java8": "/usr/lib/jvm/java-8-openjdk/bin/java",
    "java11": "/usr/lib/jvm/java-11-openjdk/bin/java",
    "java17": "/usr/lib/jvm/java-17-openjdk/bin/java",
    "java21": "/usr/lib/jvm/java-21-openjdk/bin/java",
    "default": "java" # Memanggil java dari environment system (default)
}

# ==========================================
# FUNGSI UTILITAS
# ==========================================
def setup_directories():
    if not os.path.exists(MC_DIR):
        os.makedirs(MC_DIR)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"account_type": "offline", "username": "ZertPlayer", "token": "", "uuid": ""}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def determine_java_version(version_id):
    """Logika dinamis untuk memilih JDK berdasarkan versi Minecraft"""
    try:
        v_parts = version_id.split('.')
        minor = int(v_parts[1])
        if minor <= 12: return JAVA_PATHS["java8"]
        elif minor <= 16: return JAVA_PATHS["java11"]
        elif minor <= 20 and len(v_parts) < 3: return JAVA_PATHS["java17"] # 1.17 - 1.20.4
        elif minor >= 20: return JAVA_PATHS["java21"] # 1.20.5+
    except:
        pass
    return JAVA_PATHS["default"]

# ==========================================
# SISTEM AKUN (PREMIUM & CRACK)
# ==========================================
def login_manager(config):
    title = 'Pilih Tipe Autentikasi:'
    options = ['1. Akun Offline (Crack)', '2. Akun Premium (Microsoft/Ori)', '3. Kembali']
    choice, _ = pick(options, title, indicator='=>')

    if "Offline" in choice:
        username = console.input("[bold cyan]Masukkan Username Offline: [/bold cyan]")
        config["account_type"] = "offline"
        config["username"] = username
        config["token"] = ""
        config["uuid"] = ""
        save_config(config)
        console.print(f"[bold green]Berhasil set akun Crack: {username}[/bold green]")
    
    elif "Premium" in choice:
        console.print(Panel("[bold yellow]Microsoft OAuth / Premium Login[/bold yellow]\n"
                            "Untuk GitHub Project, fitur ini membutuhkan [bold red]Azure Client ID[/bold red] resmi.\n"
                            "Saat ini dialihkan ke mode Offline untuk keamanan repository.", 
                            title="Akses Premium", expand=False))
        # Note for Dev: Gunakan modul minecraft_launcher_lib.microsoft_account di sini
        # Contoh implementasi:
        # url, state, verifier = minecraft_launcher_lib.microsoft_account.get_secure_login_data(CLIENT_ID, REDIRECT_URI)
        # console.print(f"Login di browser: {url}")
        # auth_code = input("Masukkan Code: ")
        # Lanjutkan fetching Token & UUID.
        
def select_version():
    console.print("[cyan]Mengambil data dari Arsip Mojang...[/cyan]")
    raw_versions = minecraft_launcher_lib.utils.get_version_list()
    installed = [v["id"] for v in minecraft_launcher_lib.utils.get_installed_versions(MC_DIR)]
    
    display_list = []
    for v in raw_versions:
        if v['type'] == 'release':
            status = "✅ [Terinstall]" if v['id'] in installed else "📥 [Download]"
            display_list.append(f"{v['id']} {status}")
            
    title = 'Pilih Versi Minecraft (Release Only):'
    selected, _ = pick(display_list, title, indicator='=>')
    return selected.split(" ")[0], installed

# ==========================================
# CORE: LAUNCHER & INSTALLER
# ==========================================
def main_menu():
    setup_directories()
    config = load_config()
    
    while True:
        console.clear()
        console.print(Panel(f"[bold magenta]CIHUY LAUNCHER - LINUX EDITION[/bold magenta]\n"
                            f"Status Akun: [bold green]{config['account_type'].upper()}[/bold green] | User: [bold cyan]{config['username']}[/bold cyan]\n"
                            f"Basecamp: [dim]{MC_DIR}[/dim]", 
                            expand=False))
        
        options = ['🎮 Play Minecraft', '👤 Ganti Akun', '⚙️ Cek Environment', '❌ Keluar']
        choice, _ = pick(options, 'Main Menu:', indicator='=>')
        
        if "Play" in choice:
            version, installed = select_version()
            
            # --- SISTEM DOWNLOAD DENGAN RICH PROGRESS BAR ---
            if version not in installed:
                with Progress() as progress:
                    task = progress.add_task(f"[cyan]Mengunduh Aset {version}...", total=100)
                    
                    def progress_callback(prog):
                        progress.update(task, completed=prog)
                        
                    callback = {
                        "setProgress": progress_callback,
                        "setStatus": lambda text: progress.update(task, description=f"[cyan]{text}"),
                    }
                    try:
                        minecraft_launcher_lib.install.install_minecraft_version(version, MC_DIR, callback=callback)
                    except Exception as e:
                        console.print(f"[bold red]Gagal mengunduh: {e}[/bold red]")
                        input("\nTekan Enter untuk kembali...")
                        continue

            # --- SETUP JVM & EXECUTE ---
            java_path = determine_java_version(version)
            console.print(f"\n[bold green]Menyiapkan Engine...[/bold green]")
            console.print(f"Versi: [cyan]{version}[/cyan] | Target JDK: [yellow]{java_path}[/yellow]")
            
            options_dict = {
                "username": config["username"],
                "uuid": config["uuid"] if config["account_type"] == "premium" else "",
                "token": config["token"] if config["account_type"] == "premium" else "",
                "executablePath": java_path if os.path.exists(java_path) else "java",
                "jvmArguments": ["-Xms1G", "-Xmx4G"] # RAM default 4GB untuk Linux Desktop
            }
            
            cmd = minecraft_launcher_lib.command.get_minecraft_command(version, MC_DIR, options_dict)
            
            console.print("[bold magenta]🚀 Membuka Gerbang Isekai...[/bold magenta]")
            try:
                # Gunakan subprocess.Popen agar terminal tidak terkunci saat game jalan
                subprocess.Popen(cmd, env=os.environ.copy())
                sys.exit(0)
            except Exception as e:
                console.print(f"[bold red]Crash Report: {e}[/bold red]")
                input("\nTekan Enter untuk kembali...")
                
        elif "Ganti Akun" in choice:
            login_manager(config)
            
        elif "Cek Environment" in choice:
            console.print("[bold yellow]Pengecekan Dependensi Linux:[/bold yellow]")
            for name, path in JAVA_PATHS.items():
                status = "[green]Found[/green]" if path == "java" or os.path.exists(path) else "[red]Not Found[/red]"
                console.print(f"- {name.upper()}: {path} -> {status}")
            input("\nTekan Enter untuk kembali...")
            
        elif "Keluar" in choice:
            console.print("[cyan]Sayonara![/cyan]")
            break

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[red]Dihentikan oleh user. Sayonara![/red]")
        sys.exit(0)
