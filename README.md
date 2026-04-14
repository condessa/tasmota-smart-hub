# Tasmota Smart Hub

> Gestão de dispositivos IoT Tasmota via MQTT — HCsoftware

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-lightgrey)

---

## Descrição

**Tasmota Smart Hub** é uma aplicação desktop para monitorização e controlo de dispositivos [Tasmota](https://tasmota.github.io/) através de MQTT. Permite visualizar o estado dos dispositivos em tempo real, enviar comandos, gerir Rules e acompanhar o tráfego MQTT num log integrado.

Desenvolvido com Python/Tkinter, seguindo o tema visual HCsoftware (dark theme com accent azul `#4a90d9`).

---

## Funcionalidades

- **Tabela de dispositivos** — deteta automaticamente dispositivos online/offline via tópico `LWT`
- **Painel de comandos** — secções organizadas por categoria (Energia, Telemetria, Luz, Timers, Sistema, Rede)
- **Comando personalizado** — envia qualquer comando/payload MQTT diretamente
- **Aba Rules** — consulta, edita, ativa/desativa e apaga `Rule1`, `Rule2` e `Rule3`
- **Log MQTT** — painel recolhível com histórico de mensagens enviadas/recebidas
- **Configuração de Broker** — guarda host, porta, utilizador e password em ficheiro local
- **Duplo clique** — TOGGLE rápido no relay (dispositivo `porta` envia `Power2 ON`)
- **LEDs de estado** — indicadores visuais verde/vermelho/cinzento por dispositivo

---

## Requisitos

| Dependência    | Versão mínima |
|----------------|---------------|
| Python         | 3.10+         |
| paho-mqtt      | 2.0+          |
| Pillow         | 10.0+         |
| tkinter        | (stdlib)       |

---

## Instalação (desenvolvimento)

```bash
# Clonar o repositório
git clone https://github.com/condessa/tasmota-smart-hub.git
cd tasmota-smart-hub

# Instalar dependências com UV
uv add paho-mqtt pillow

# Executar
uv run main.py
```

---

## Configuração MQTT

Na primeira execução, clica em **⚙ Broker MQTT** para configurar:

| Campo        | Exemplo         |
|--------------|-----------------|
| Host / IP    | `192.168.1.100` |
| Porta        | `1883`          |
| Utilizador   | `mqtt_user`     |
| Password     | `****`          |

A configuração é guardada em `tasmota_mqtt_config.json` (na pasta do programa).

---

## Estrutura do projeto

```
tasmota-smart-hub/
├── main.py                      # Aplicação principal
├── imagens/
│   └── HCsoftware.png           # Logótipo HCsoftware
├── tasmota_mqtt_config.json     # Gerado automaticamente
├── requirements.txt
└── README.md
```

---

## Tópicos MQTT subscritos

| Tópico             | Utilização                        |
|--------------------|-----------------------------------|
| `tele/+/LWT`       | Deteção online/offline            |
| `stat/+/POWER`     | Estado do relay                   |
| `stat/+/RESULT`    | Resposta a comandos               |
| `tele/+/STATE`     | Telemetria de estado              |

---

## Instalação via .deb (Linux)

```bash
sudo dpkg -i tasmota-smart-hub_1.0.0_amd64.deb
tasmota-smart-hub
```

---

## Autor

**HCsoftware** · [github.com/condessa](https://github.com/condessa)

---

## Licença

MIT License — usa livremente, mantém a referência ao autor.
