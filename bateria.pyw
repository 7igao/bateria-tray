import subprocess, threading, time
import hid
from PIL import Image, ImageDraw, ImageFont
import pystray

dispositivo = "JBL"

def bateria_jbl(nome="JBL"):
    ps = (
        f"$on = Get-PnpDevice -Class AudioEndpoint | "
        f"Where {{ $_.FriendlyName -like '*{nome}*' -and $_.Status -eq 'OK' }}; "
        "if (-not $on) { exit }; "
        f"Get-PnpDevice | Where FriendlyName -like '*{nome}*' | "
        "ForEach { (Get-PnpDeviceProperty -InstanceId $_.InstanceId "
        "-KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2' "
        "-ErrorAction SilentlyContinue).Data } | Where { $_ -ne $null } | Select -First 1"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        return int(r.stdout.strip()), False
    except ValueError:
        return None, False

def bateria_dualsense():
    """Retorna (nivel, carregando)."""
    try:
        d = hid.device()
        d.open(0x054C, 0x0CE6)
        try:
            d.get_feature_report(0x05, 41)
        except Exception:
            pass
        for _ in range(20):
            rep = d.read(100, 1000)
            if not rep:
                continue
            if rep[0] == 0x31 and len(rep) > 54:
                status = rep[54]
            elif rep[0] == 0x01 and len(rep) >= 64:
                status = rep[53]
            else:
                continue
            d.close()
            estado = status >> 4
            nivel = 100 if estado == 2 else min((status & 0x0F) * 10 + 5, 100)
            return nivel, estado in (1, 2)
        d.close()
    except Exception:
        pass
    return None, False

def desenha_icone(valor, carregando=False):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    txt = "?" if valor is None else str(valor)
    if carregando:
        cor = (80, 220, 100)
    elif valor is None or valor > 20:
        cor = (255, 255, 255)
    else:
        cor = (255, 70, 70)

    if carregando:
        tamanho = 40 if len(txt) < 3 else 30
        fonte = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", tamanho)
        # número um pouco abaixo e à direita, para abrir espaço pro raio
        dr.text((34, 39), txt, font=fonte, fill=cor, anchor="mm")
        # raio pequeno no canto superior esquerdo
        raio = [(13, 1), (3, 13), (8, 13), (5, 23), (17, 9), (11, 9), (15, 1)]
        dr.polygon(raio, fill=(255, 210, 0))
    else:
        tamanho = 44 if len(txt) < 3 else 34
        fonte = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", tamanho)
        dr.text((32, 32), txt, font=fonte, fill=cor, anchor="mm")
    return img

def atualizar_agora(icon):
    if dispositivo == "JBL":
        nivel, carregando = bateria_jbl()
    else:
        nivel, carregando = bateria_dualsense()
    icon.icon = desenha_icone(nivel, carregando)
    extra = " (carregando)" if carregando else ""
    icon.title = f"{dispositivo}: {nivel if nivel is not None else '?'}%{extra}"

def loop(icon):
    while True:
        atualizar_agora(icon)
        time.sleep(30)

def escolhe(nome):
    def _f(icon, item):
        global dispositivo
        dispositivo = nome
        threading.Thread(target=atualizar_agora, args=(icon,), daemon=True).start()
    return _f

def clique_atualizar(icon, item):
    threading.Thread(target=atualizar_agora, args=(icon,), daemon=True).start()

menu = pystray.Menu(
    pystray.MenuItem("Fone JBL", escolhe("JBL"), checked=lambda i: dispositivo == "JBL", radio=True),
    pystray.MenuItem("DualSense", escolhe("DualSense"), checked=lambda i: dispositivo == "DualSense", radio=True),
    pystray.MenuItem("Atualizar agora", clique_atualizar),
    pystray.MenuItem("Sair", lambda icon, item: icon.stop()),
)

icon = pystray.Icon("bateria", desenha_icone(None), "Bateria", menu)
threading.Thread(target=loop, args=(icon,), daemon=True).start()
icon.run()
icon.run()