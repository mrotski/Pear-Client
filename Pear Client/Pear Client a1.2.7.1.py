import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import json
import urllib.request

# versions
versions = ["1.19.4", "1.20.4", "1.21.10"]

# Paths
base_dir = os.path.dirname(__file__)
java_path = "java.exe"
lwjgl_path = r"C:\PearClient-main\PearClient\Natives\lwjgl-3.3.1"
game_dir = r"C:\PearClient-main\PearClient\needed_files\data_minecraft"
libraries_path = os.path.join(game_dir, "libraries")
assets_dir = os.path.join(game_dir, "assets")
versions_dir = os.path.join(game_dir, "versions")

def fetch_version_manifest():
    url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    try:
        with urllib.request.urlopen(url) as response:
            return json.load(response)
    except Exception as e:
        messagebox.showerror("We ran into an error", f"Manifest download failed:\n{e}")
        return None

def download_version_files(version_id, versions_dir):
    manifest = fetch_version_manifest()
    if not manifest:
        return False

    version_info = next((v for v in manifest["versions"] if v["id"] == version_id), None)
    if not version_info:
        messagebox.showerror("We ran into an error", f"Version {version_id} not found in the files.")
        return False

    try:
        with urllib.request.urlopen(version_info["url"]) as response:
            version_json = json.load(response)
    except Exception as e:
        messagebox.showerror("We ran into an error", f"JSON download failed:\n{e}")
        return False

    version_path = os.path.join(versions_dir, version_id)
    os.makedirs(version_path, exist_ok=True)

    json_path = os.path.join(version_path, f"{version_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(version_json, f, indent=2)

    jar_info = version_json.get("downloads", {}).get("client", {})
    jar_url = jar_info.get("url")
    jar_path = os.path.join(version_path, f"{version_id}.jar")

    if jar_url:
        try:
            urllib.request.urlretrieve(jar_url, jar_path)
        except Exception as e:
            messagebox.showerror("We ran into an error", f"JAR download failed:\n{e}")
            return False

    return True

def ensure_version_files(version):
    version_dir = os.path.join(versions_dir, version)
    json_path = os.path.join(version_dir, f"{version}.json")
    if not os.path.exists(json_path):
        success = download_version_files(version, versions_dir)
        if not success:
            return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def download_missing_libraries(libraries, libraries_path):
    base_url = "https://libraries.minecraft.net"
    for lib in libraries:
        if "downloads" in lib and "artifact" in lib["downloads"]:
            artifact = lib["downloads"]["artifact"]
            rel_path = artifact["path"]
            url = f"{base_url}/{rel_path}"
            dest_path = os.path.join(libraries_path, rel_path)
            if not os.path.exists(dest_path):
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                try:
                    print(f"Downloading libraries: {url}")
                    urllib.request.urlretrieve(url, dest_path)
                except Exception as e:
                    print(f"We encountered an unexpected error when downloading a library: {rel_path}\n{e}")

def download_asset_index(asset_index, asset_index_path):
    asset_index_url = asset_index["url"]
    try:
        with urllib.request.urlopen(asset_index_url) as response:
            data = json.load(response)
        os.makedirs(os.path.dirname(asset_index_path), exist_ok=True)
        with open(asset_index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data
    except Exception as e:
        messagebox.showerror("We ran into an error", f"Assets_index download failed:\n{e}")
        return None

def download_missing_assets(asset_index, objects_dir):
    for key, obj in asset_index["objects"].items():
        hash_val = obj["hash"]
        subdir = hash_val[:2]
        file_path = os.path.join(objects_dir, subdir, hash_val)
        if not os.path.exists(file_path):
            url = f"https://resources.download.minecraft.net/{subdir}/{hash_val}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            try:
                print(f"Downloading asset: {key}")
                urllib.request.urlretrieve(url, file_path)
            except Exception as e:
                print(f"We encountered an unexpected error when downloading asset: {key}\n{e}")

def build_classpath(version_json, version_dir):
    classpath = []
    for lib in version_json["libraries"]:
        if "downloads" in lib and "artifact" in lib["downloads"]:
            rel_path = lib["downloads"]["artifact"]["path"]
            classpath.append(os.path.join(libraries_path, rel_path))
    classpath.append(os.path.join(version_dir, f"{version_json['id']}.jar"))
    for jar in ["lwjgl.jar", "lwjgl-glfw.jar", "lwjgl-opengl.jar",
                "lwjgl-openal.jar", "lwjgl-stb.jar", "lwjgl-tinyfd.jar", "lwjgl-jemalloc.jar"]:
        classpath.append(os.path.join(lwjgl_path, jar))
    return classpath

def launch_game():
    version = version_var.get()
    username = username_var.get().strip()
    print(f"== Starting: {version}")
    print(f"== Username: {username}")

    if not username:
        messagebox.showerror("You silly...", "Username can't be blank.")
        return

    version_json = ensure_version_files(version)
    if not version_json:
        print("Version JSON download failed.")
        return
    print("== Version JSON downloaded.")

    print(f"== Libraries: {len(version_json['libraries'])}")
    download_missing_libraries(version_json["libraries"], libraries_path)

    asset_index_id = version_json["assetIndex"]["id"]
    asset_index_path = os.path.join(assets_dir, "indexes", f"{asset_index_id}.json")
    objects_dir = os.path.join(assets_dir, "objects")

    print(f"== Asset_index ID: {asset_index_id}")
    if not os.path.exists(asset_index_path):
        asset_index = download_asset_index(version_json["assetIndex"], asset_index_path)
        if not asset_index:
            print("Asset_index downloading failed.")
            return
    else:
        with open(asset_index_path, "r", encoding="utf-8") as f:
            asset_index = json.load(f)

    print(f"== Assets: {len(asset_index['objects'])}")
    download_missing_assets(asset_index, objects_dir)

    version_dir = os.path.join(versions_dir, version)
    classpath = build_classpath(version_json, version_dir)
    print(f"== Classpath ({len(classpath)} tiedostoa):")
    for cp in classpath:
        print("   ", cp)

    natives_path = os.path.join(lwjgl_path, "win-nat")
    print(f"== starting up mainClass: {version_json['mainClass']}")

    try:
        with open("error_log.txt", "w") as err:
            subprocess.Popen([
                java_path,
                "-Xmx2G", "-Xms1G",
                f"-Djava.library.path={natives_path}",
                "-cp", ";".join(classpath),
                version_json["mainClass"],
                "--username", username,
                "--version", version,
                "--gameDir", game_dir,
                "--assetsDir", assets_dir,
                "--assetIndex", asset_index_id,
                "--uuid", "00000000-0000-0000-0000-000000000000",
                "--accessToken", "Pear-access-token",
                "--userType", "mojang"
            ], stdout=err, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("Startup", f"Minecraft {version} is starting!")
    except Exception as e:
        print("Startup failed:", e)
        messagebox.showerror("ERR", f"Startup failed:\n{e}")
        os.startfile("error_log.txt")

# GUI
root = tk.Tk()
root.title("Pear Client Alpha 1.2.7")
root.geometry("640x480")
root.configure(bg="#2e8b57")

main_frame = tk.Frame(root, bg="#2e8b57")
main_frame.pack(expand=True)

tk.Label(main_frame, text="PearClient A1.2", font=("Helvetica", 20, "bold"), fg="white", bg="#2e8b57").pack(pady=20)

tk.Label(main_frame, text="Choose version:", font=("Helvetica", 14), fg="white", bg="#2e8b57").pack()
version_var = tk.StringVar(value=versions[0])
version_menu = tk.OptionMenu(main_frame, version_var, *versions)
version_menu.config(font=("Helvetica", 12), width=15)
version_menu.pack(pady=5)

username_label = tk.Label(main_frame, text="Type your username:", font=("Helvetica", 14), fg="white", bg="#2e8b57")
username_label.pack(pady=10)
username_var = tk.StringVar()
username_entry = tk.Entry(main_frame, textvariable=username_var, font=("Helvetica", 12), width=20)
username_entry.pack(pady=5)

launch_button = tk.Button(
    main_frame,
    text="Launch Minecraft!",
    command=launch_game,
    font=("Helvetica", 14),
    bg="#4CAF50",
    fg="white"
)
launch_button.pack(pady=20)
root.mainloop()

