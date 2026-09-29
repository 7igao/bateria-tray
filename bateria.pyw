import subprocess, threading, time
import hid
from PIL import Image, ImageDraw, ImageFont
import pystray

dispositivo = "JBL"
nivel = None

def bateria_jbl(nome="JBL"):
    ps = (
        f"Get-PnpDevice | Where FriendlyName -like '*{nome}*' | "
        "ForEach { (Get-PnpDeviceProperty -InstanceId $_.InstanceId "
        "-KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2' "
        "-ErrorAction SilentlyContinue).Data } | Where { $_ -ne $null } | Select -First 1"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return None

def bateria_dualsense():
    try:
        d = hid.device()
        d.open(0x054C, 0x0CE6)          
        try:
            d.get_feature_report(0x05, 41)  
        except Exception:
            pass
        d.set_nonblocking(False)
        for _ in range(20):
            rep = d.read(100, 1000)
            if not rep:
                continue
            if rep[0] == 0x31 and len(rep) > 54:      
                status = rep[54]
            elif rep[0] == 0x01 and len(rep) > 53 and len(rep) >= 64:  
                status = rep[53]
            else:
                continue
            d.close()
            return min((status & 0x0F) * 10 + 5, 100)
        d.close()
    except Exception:
        pass
    return None

def desenha_icone(valor):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    txt = "?" if valor is None else str(valor)
    cor = (255, 255, 255) if valor is None or valor > 20 else (255, 70, 70)
    fonte = ImageFont.truetype("arialbd.ttf", 44 if len(txt) < 3 else 34)
    dr.text((32, 32), txt, font=fonte, fill=cor, anchor="mm")
    return img

def atualiza(icon):
    global nivel
    while True:
        nivel = bateria_jbl() if dispositivo == "JBL" else bateria_dualsense()
        icon.icon = desenha_icone(nivel)
        icon.title = f"{dispositivo}: {nivel if nivel is not None else '?'}%"
        time.sleep(10)

def escolhe(nome):
    def _f(icon, item):
        global dispositivo
        dispositivo = nome
    return _f

menu = pystray.Menu(
    pystray.MenuItem("Fone JBL", escolhe("JBL"), checked=lambda i: dispositivo == "JBL", radio=True),
    pystray.MenuItem("DualSense", escolhe("DualSense"), checked=lambda i: dispositivo == "DualSense", radio=True),
    pystray.MenuItem("Sair", lambda icon, item: icon.stop()),
)

icon = pystray.Icon("bateria", desenha_icone(None), "Bateria", menu)
threading.Thread(target=atualiza, args=(icon,), daemon=True).start()
icon.run()