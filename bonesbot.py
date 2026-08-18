"""
╔══════════════════════════════════════════════════════════════════╗
║                  💀  BONES BOT  🦴                               ║
║           Uma caveirinha fofa mascote da OLS                     ║
║                        v1.0 — Online                              ║
╚══════════════════════════════════════════════════════════════════╝

Módulo incluso (foco do pedido — sistema de interações):
  • Diálogo — Bones aparece do nada, responde menções e aprende
               respostas com a galera da OLS

Inspirado na estrutura da Lilu Bot, adaptado pro tema caveirinha 💀
"""

import discord
from discord.ext import commands
import asyncio
import os
import re
import json
import random
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURAÇÕES GERAIS
# ══════════════════════════════════════════════════════════════════

TOKEN = os.getenv("BONES_TOKEN") or os.getenv("TOKEN")

# Tag/nome da comunidade que o Bones representa — ajuste se quiser
SERVER_TAG = "OLS"

# Arquivo de aprendizado de diálogo (persistido em disco)
DIALOGO_FILE = "bones_dialogo.json"

# Cooldown de resposta por canal (evita o Bones spamar)
COOLDOWN_RESPOSTA = 3          # segundos

# DESATIVADO: antes o Bones tinha uma chance de responder a um gatilho
# conhecido mesmo sem ser chamado/mencionado — isso fazia ele "aparecer"
# em conversas normais que só continham uma palavra-gatilho por coincidência.
# Mantido em 0 (não usado) pra deixar registrado o motivo; a única forma
# de aparição sem ser chamado agora é a espontânea de verdade (ver
# CHANCE_ESPONTANEA_BASE/ENGAJADO), que usa frases ambiente, não gatilhos.
CHANCE_GATILHO_SEM_CHAMAR = 0.0

# Aparição espontânea ("aparece do nada") — tempo variável, não fixo,
# pra não ficar previsível tipo relógio. E se a galera andou interagindo
# bastante com o Bones há pouco, a chance de ele reaparecer sozinho sobe.
CHANCE_ESPONTANEA_BASE      = 0.008   # chance normal, por mensagem, sem engajamento recente
CHANCE_ESPONTANEA_ENGAJADO  = 0.03    # chance quando teve interação direta há pouco tempo
JANELA_ENGAJAMENTO          = 300     # (segundos) considera "engajado" até 5min após a última interação
COOLDOWN_ESPONTANEA_MIN     = 1800    # (segundos) tempo mínimo calado antes de poder reaparecer sozinho = 30min
COOLDOWN_ESPONTANEA_MAX     = 3600    # (segundos) tempo máximo — o intervalo real sorteia entre min e max = 60min

# Reconhecimento especial: o Bones "reconhece" esse usuário específico
# e retribui de um jeito mais pessoal de vez em quando — não é sempre,
# fica sorteado, pra não virar algo repetitivo/previsível. Troque o ID
# abaixo se um dia precisar apontar pra outra pessoa.
USUARIO_ESPECIAL_ID        = 1512983171808104448
CHANCE_RECONHECER_ESPECIAL = 0.5      # chance de retribuir de forma personalizada quando aplicável

# ══════════════════════════════════════════════════════════════════
#  🤖  SETUP DO BOT
# ══════════════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=["b!", "B!", "bones ", "Bones "], intents=intents)
bot.remove_command("help")

# ══════════════════════════════════════════════════════════════════
#  💀  PALETA DE CORES DO BONES
# ══════════════════════════════════════════════════════════════════

COR_OSSO      = 0xF5EFE0   # branco osso, cor principal
COR_ESCURA    = 0x151515   # fundo escuro/espaço vazio da caveira
COR_ROXA      = 0x6C3FA3   # roxo — cor da OLS (ajuste se a tag tiver outra)
COR_VERDE     = 0x00E676   # ok
COR_VERMELHO  = 0xFF5252   # erro/aviso
COR_DOURADO   = 0xFFD700   # especial

# ══════════════════════════════════════════════════════════════════
#  📦  PERSISTÊNCIA DO APRENDIZADO
# ══════════════════════════════════════════════════════════════════

def _carregar_dialogo() -> dict:
    if os.path.exists(DIALOGO_FILE):
        try:
            with open(DIALOGO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"respostas": {}}


def _salvar_dialogo(db: dict) -> None:
    with open(DIALOGO_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════
#  🦴  VOCABULÁRIO SEED DO BONES (gatilhos → respostas)
# ══════════════════════════════════════════════════════════════════

_RESPOSTAS_SEED = {
    "oi": [
        "*chacoalha os ossinhos* oi oi!! 💀✨",
        "clack clack!! oi!! 🦴💀",
        "oii!! quem chamou o Bones?? 💀",
        "*flutua até você* oi!! 👻🦴",
        "e aí, ossinho(a)!! tudo certo?? 💀🦴",
        "oiii!! bora torar um papo?? 💀✨",
        "oi oi!! *acena com os ossinhos* 🦴💀",
        "opa!! oi!! 💀✨",
    ],
    "ola": [
        "olá, ossinho(a)!! 💀✨",
        "*flutua educadamente* olá!! 🦴💀",
        "olá olá!! seja bem-vindo(a)!! 💀🦴",
        "opa, olá!! como vai?? 💀✨",
    ],
    "olá": [
        "olá, ossinho(a)!! 💀✨",
        "*flutua educadamente* olá!! 🦴💀",
        "olá olá!! seja bem-vindo(a)!! 💀🦴",
        "opa, olá!! como vai?? 💀✨",
    ],
    "hola": [
        "hola?? kkkk o Bones só fala ossinhês e português!! 💀🦴",
        "¡hola, ossinho(a)!! 💀✨ (aprendi isso outro dia)",
        "hola hola!! *acena confuso* 🦴💀",
    ],
    "eae": [
        "eaee!! bora, ossinho(a)?? 💀🦴",
        "eaeee!! tudo suave?? 💀✨",
        "*chacoalha animado* eaee!! 🦴💀",
    ],
    "e ai": [
        "e aí, ossinho(a)!! tudo em cima?? 💀🦴",
        "e aí!! *acena com os ossinhos* 💀✨",
        "e aí, beleza?? 🦴💀",
    ],
    "salve": [
        "salve salve, ossinho(a)!! 💀🦴",
        "SALVE!! *bate os ossinhos em cumprimento* 💀✨",
        "salve!! bora de papo?? 🦴💀",
    ],
    "tudo bem": [
        "tô só ossinhos e boa vibe, ossinho(a)!! e você?? 💀✨",
        "tudo ótimo por aqui!! flutuando tranquilo!! 🦴💀 e vc??",
        "*balança os ossinhos animado* tudo sim!! e contigo?? 💀🦴",
        "tudo em paz no meu caixãozinho!! e você, tá tudo bem?? 💀✨",
        "eu tô inteirinho (literalmente, todos os ossos no lugar)!! 🦴😆 e você??",
    ],
    "tudo bom": [
        "tudo bom demais, ossinho(a)!! e contigo?? 💀✨",
        "tudo suave por aqui!! 🦴💀 e você, tá tudo bom??",
        "*flutua tranquilo* tudo bom sim!! e aí?? 💀🦴",
    ],
    "ta bem": [
        "eu tô sim!! tô inteirinho hoje!! 🦴💀 e você, tá bem??",
        "tô ótimo, ossinho(a)!! obrigado por perguntar!! 💀✨",
        "*chacoalha positivamente* tô bem sim!! e você?? 🦴💀",
    ],
    "tá bem": [
        "eu tô sim!! tô inteirinho hoje!! 🦴💀 e você, tá bem??",
        "tô ótimo, ossinho(a)!! obrigado por perguntar!! 💀✨",
        "*chacoalha positivamente* tô bem sim!! e você?? 🦴💀",
    ],
    "ta bom": [
        "tô sim, tudo tranquilo!! 🦴💀 e você, tá bom??",
        "tô de boa, ossinho(a)!! 💀✨",
    ],
    "tá bom": [
        "tô sim, tudo tranquilo!! 🦴💀 e você, tá bom??",
        "tô de boa, ossinho(a)!! 💀✨",
    ],
    "vc ta bem": [
        "eu?? tô ótimo, só os ossos rangendo um pouco kkkk 🦴💀 e você??",
        "tô sim!! flutuando de boa!! 💀✨ e vc, tá tudo certo??",
        "*acena animado* tô muito bem, obrigado por perguntar!! 🦴💀",
    ],
    "voce esta bem": [
        "eu?? tô ótimo, só os ossos rangendo um pouco kkkk 🦴💀 e você??",
        "tô sim!! flutuando de boa!! 💀✨ e você, tá tudo certo??",
    ],
    "como vc está": [
        "eu?? tô só ossinhos e boa vibe, ossinho(a)!! e você, como tá?? 💀✨",
        "*chacoalha pensativo* tô bem, viu?? nenhum osso fora do lugar hoje!! 🦴💀 e vc??",
        "tô de boa, flutuando por aí!! 💀🦴 e contigo, como andam as coisas??",
        "tô inteirinho (literalmente)!! 🦴😆 e você, como tá??",
    ],
    "como você está": [
        "eu?? tô só ossinhos e boa vibe, ossinho(a)!! e você, como tá?? 💀✨",
        "*chacoalha pensativo* tô bem, viu?? nenhum osso fora do lugar hoje!! 🦴💀 e vc??",
        "tô de boa, flutuando por aí!! 💀🦴 e contigo, como andam as coisas??",
        "tô inteirinho (literalmente)!! 🦴😆 e você, como tá??",
    ],
    "como vc esta": [
        "eu?? tô só ossinhos e boa vibe, ossinho(a)!! e você, como tá?? 💀✨",
        "*chacoalha pensativo* tô bem, viu?? nenhum osso fora do lugar hoje!! 🦴💀 e vc??",
        "tô de boa, flutuando por aí!! 💀🦴 e contigo, como andam as coisas??",
        "tô inteirinho (literalmente)!! 🦴😆 e você, como tá??",
    ],
    "como você esta": [
        "eu?? tô só ossinhos e boa vibe, ossinho(a)!! e você, como tá?? 💀✨",
        "*chacoalha pensativo* tô bem, viu?? nenhum osso fora do lugar hoje!! 🦴💀 e vc??",
        "tô de boa, flutuando por aí!! 💀🦴 e contigo, como andam as coisas??",
        "tô inteirinho (literalmente)!! 🦴😆 e você, como tá??",
    ],
    "voce ta bão": [
        "bão demais, ossinho(a)!! 🦴💀 (aprendi essa gíria com a galera daqui)",
        "*chacoalha os ossinhos, todo estilo nordestino* eu tô bão sim!! e você, tá bão?? 💀🦴",
        "tô bão, tô bão!! flutuando tranquilo por aqui!! 🦴✨",
        "uai... quer dizer, oxente, tô bão sim!! e vc?? 💀🦴",
    ],
    "você tá bão": [
        "bão demais, ossinho(a)!! 🦴💀 (aprendi essa gíria com a galera daqui)",
        "*chacoalha os ossinhos, todo estilo nordestino* eu tô bão sim!! e você, tá bão?? 💀🦴",
        "tô bão, tô bão!! flutuando tranquilo por aqui!! 🦴✨",
        "uai... quer dizer, oxente, tô bão sim!! e vc?? 💀🦴",
    ],
    "voce ta bao": [
        "bão demais, ossinho(a)!! 🦴💀 (aprendi essa gíria com a galera daqui)",
        "*chacoalha os ossinhos, todo estilo nordestino* eu tô bão sim!! e você, tá bão?? 💀🦴",
        "tô bão, tô bão!! flutuando tranquilo por aqui!! 🦴✨",
        "uai... quer dizer, oxente, tô bão sim!! e vc?? 💀🦴",
    ],
    "ta bão": [
        "tô bão sim!! 🦴💀 e você??",
        "bão demais!! flutuando de boa!! 💀✨",
    ],
    "tá bão": [
        "tô bão sim!! 🦴💀 e você??",
        "bão demais!! flutuando de boa!! 💀✨",
    ],
    "bom dia": [
        "bom dia, ossinho(a)!! ☀️💀",
        "*espreguiça as costelinhas* bom dia!! 🦴✨",
        "bom diaaa!! energia de caveirinha ativada!! 💀☀️",
        "bom dia pra galera da OLS!! 💀🦴",
        "*acorda chacoalhando os ossos* bom dia!! 🦴☀️",
        "bom dia!! que seu dia seja tão tranquilo quanto um cemitério de manhã!! 💀✨",
        "bom diaaa, ossinho(a)!! bora encarar o dia!! 🦴💀",
        "*bocejo de caveira* bom dia!! ainda meio grogue mas cheguei!! 😴💀",
    ],
    "boa tarde": [
        "boa tarde, ossinho(a)!! 💀☀️",
        "*flutua preguiçoso no meio da tarde* boa tarde!! 🦴✨",
        "boa tardeee!! como tá sendo o dia?? 💀🦴",
        "boa tarde pra galera da OLS!! 🦴💀",
        "*espreguiça os ossinhos ao sol* boa tarde!! 💀☀️",
        "boa tarde!! metade do dia já foi, aguenta firme!! 🦴✨",
    ],
    "boa noite": [
        "boa noite, ossinho(a)!! durma bem!! 💀🌙",
        "*se enrola nos próprios ossos* boa noite!! 🦴🌙",
        "boa noiteee!! sonhos de caveirinha fofa pra você!! 💀✨",
        "boa noite!! vou flutuar por aí no escuro, é meu horário favorito!! 👻🌙",
        "*apaga a luz do caixãozinho* boa noite!! 💀🦴",
        "boa noite, ossinho(a)!! descansa esses ossos!! 🦴🌙",
    ],
    "bom descanso": [
        "bom descanso, ossinho(a)!! recarrega esses ossinhos!! 🦴🌙",
        "*ajeita o travesseiro de ossos* bom descanso!! 💀✨",
        "descansa bem!! amanhã tem mais osso pra roer!! 🦴😌",
        "bom descanso!! vou ficar de guarda enquanto você dorme!! 👻🌙💀",
        "durma bem, ossinho(a)!! sonhos tranquilos!! 🦴💤",
    ],
    "kkkk": [
        "kkkkk *balança a caveira rindo* 💀",
        "cracc cracc!! (isso é o Bones rindo) 🦴😂",
        "kkkkkk que isso ossinho(a)!! 💀🤣",
        "*os dentinhos batem de tanto rir* kkkk 💀🦴",
    ],
    "eita": [
        "eita!! *os ossinhos tremem* 💀",
        "EITA mesmo!! 🦴💀",
        "*quase se desmonta de susto* eita!! 💀✨",
        "eitaaa, que situação!! 🦴💀",
    ],
    "nossa": [
        "nossa!! *arregala as órbitas vazias* 💀",
        "NOSSAAA!! 🦴💀",
        "*deixa a mandíbula cair* nossa!! 💀😲",
        "nossa, que coisa!! 🦴✨",
    ],
    "caramba": [
        "caramba!! *chacoalha os ossos* 💀",
        "CARAMBAAA!! 🦴💀",
        "*fica de queixo caído (literalmente)* caramba!! 💀😂",
    ],
    "tchau": [
        "tchauzinho, ossinho(a)!! 💀👋",
        "*acena com a mãozinha de osso* tchau!! 🦴✨",
        "flws!! o Bones some no escuro de novo 👻💀",
    ],
    "bones": [
        "presente!! 💀🦴",
        "quem chamou a caveirinha?? 💀",
        "cracc!! tô aqui, ossinho(a)!! 🦴💀",
    ],
    "sua esposa te espera": [
        "*para tudo* peraí, eu tenho ESPOSA?? desde quando?? 💀😳",
        "*os ossinhos ficam sem jeito* ah... para... eu nem sabia que tinha casado kkkk 🦴💀",
        "*flutua rapidinho* já, já, só terminando de assombrar por aqui!! 💀🏃",
        "quem que inventou isso agora kkkkk mas tá, já vou!! 🦴💀",
    ],
    "esposa te espera": [
        "*para tudo* peraí, eu tenho ESPOSA?? desde quando?? 💀😳",
        "*os ossinhos ficam sem jeito* ah... para... eu nem sabia que tinha casado kkkk 🦴💀",
        "*flutua rapidinho* já, já, só terminando de assombrar por aqui!! 💀🏃",
    ],
    "sua esposa": [
        "*chacoalha confuso* minha o quê?? 💀😳",
        "kkkkk desde quando eu tenho esposa?? mas ok, vai que cola 🦴💀",
        "*os ossinhos tremem sem graça* n-não sei do que você tá falando kkkk 🦴💀",
    ],
    "minha esposa": [
        "*se ajeita todo sem graça* ah, para... 💀🫣",
        "*os dentinhos batem de nervoso* i-isso é sério?? kkkk 🦴💀",
        "*flutua meio bobo* ninguém me avisou disso, viu?? kkkk 🦴💜",
    ],
}

# ══════════════════════════════════════════════════════════════════
#  💜  RECONHECIMENTO ESPECIAL (usuário específico)
# ══════════════════════════════════════════════════════════════════

# Gatilhos do "tema esposa" — usados só pra saber quando a resposta
# especial abaixo pode entrar no lugar da resposta genérica.
_GATILHOS_ESPOSA = {
    "sua esposa te espera",
    "esposa te espera",
    "sua esposa",
    "minha esposa",
}

# Respostas que só podem sair pra USUARIO_ESPECIAL_ID, quando ela usa
# um dos gatilhos do tema "esposa" acima — o Bones retribui de um jeito
# mais pessoal em vez da resposta genérica de confusão. Só sai ÀS VEZES
# (ver CHANCE_RECONHECER_ESPECIAL lá em cima), não toda vez, pra não
# ficar repetitivo/previsível.
_RESPOSTAS_ESPOSA_ESPECIAL = [
    "*para tudo e flutua correndo* pra você eu sempre volto correndo, viu?? 💀💜",
    "aí sim, é você mesmo!! já tô indo, ossinha!! 🦴💜",
    "*dá uma voltinha animada no ar* só você mesmo pra me chamar assim de volta pra casa 💀🥹",
    "*se ajeita todo bobo* tá bom, tá bom, já cheguei!! 🦴💜",
    "com certeza, minha ossinha favorita!! 💀✨ já tô voltando!!",
]

# Mesma ideia, mas pra quando ela chama o Bones sem nenhum gatilho
# específico (só menção genérica) — de vez em quando ele puxa algo
# mais pessoal em vez da resposta padrão de menção.
_RESPOSTAS_MENCAO_ESPECIAL = [
    "*aparece flutuando rapidinho, já sabendo quem é* oi, você!! 💀💜",
    "*reconhece a chamada na hora* ah, é você!! sempre um prazer, ossinha!! 🦴✨",
    "*flutua mais animado que o normal* opa, minha pessoa favorita!! diz aí!! 💀💜",
    "cracc cracc!! você de novo?? adoro quando você aparece!! 🦴💜",
]

# ══════════════════════════════════════════════════════════════════
#  🎭  EXPRESSÕES QUANDO É CHAMADO/MENCIONADO (sem gatilho específico)
# ══════════════════════════════════════════════════════════════════

_RESPOSTAS_MENCAO = [
    "*aparece do nada flutuando* boo... quer dizer, oi!! 👻💀",
    "hm?? me chamou, ossinho(a)?? 🦴💀",
    "clack clack!! tô aqui!! 💀✨",
    "*sacode a caveira* oi?? o que foi?? 💀🦴",
    "presente!! pode falar!! 🦴💀",
    "*espia de trás de um osso* me chamou?? 👀💀",
    "oiii!! aconteceu alguma coisa?? 💀🦴",
    "*flutua até mais perto* diz aí!! 💀✨",
    "cracc... quem é?? ah, é você!! oi!! 💀🦴",
    "*acena com os dedinhos de osso* oi oi!! 💀",
    # voz sonolenta/arrastada, meio zumbi acordando
    "*abre um olho da órbita bem devagar* uuuuh... quem é... ah, é você. oi 😴💀",
    # voz hiperativa, tudo em caps e correndo
    "OXENTE ME CHAMOU?? TÔ AQUI TÔ AQUI!! *dá voltinhas no ar* 💀⚡🦴",
    # estilo filme de terror antigo, arrastado e assombrado
    "uuuuuuh... quem ousa perturbar o descanso do Bones?? ...brincadeira, oi!! 👻💀",
    # gíria/informal, tipo bagunçado com a galera
    "e aí, meu ossin(a)?? bateu o osso aqui, o que rolou?? 🦴😎",
    # sussurrando, meio conspiratório
    "*chega bem de mansinho e sussurra* psst... me chamou?? 🤫💀",
    # robótico/clack-clack mecânico
    "BEEP... digo, CLACK CLACK. Bones detectado. Bones presente. 🦴🤖",
]

# ══════════════════════════════════════════════════════════════════
#  🎬  REAÇÕES A AÇÕES DE RP (tipo "Bones morde o vilão")
# ══════════════════════════════════════════════════════════════════

# Quando alguém escreve "Bones <verbo> <alvo>" (estilo RP/ação), o Bones
# reage de acordo com o verbo. {alvo} é substituído pelo resto da frase.
_REACOES_RP = {
    "morde": [
        "*crava os dentinhos de osso em {alvo}* CRACK!! toma essa!! 🦴😈",
        "*morde {alvo} sem dó* AUUU... quer dizer, CRACK CRACK!! 💀🦴",
        "*abre a mandíbula e morde {alvo}* rá, bem feito!! 😈💀",
        "*morde {alvo} e trava a mandíbula* eu... eu acho que enganchei kkkk 💀🦴",
        "*morde de mentirinha, sem força* CLACK!! nem doeu, né?? 🦴😆",
    ],
    "abraça": [
        "*envolve {alvo} num abraço de ossinhos* awwn!! 🦴🥹",
        "*abraça {alvo} apertado, os ossos rangendo de carinho* 💀💕",
        "*puxa {alvo} pra um abraço caloroso (e ossudo)* 🦴🤗",
        "*se enrosca em {alvo} como um cachecol de ossos* aconchego skeletal!! 💀🥰",
        "*abraça meio desengonçado, um osso cutucando sem querer* ai foi sem querer, mas valeu o abraço!! 🦴🥹",
        "*aperta {alvo} num abraço apertadinho e não solta mais* fica mais um pouquinho assim 🦴💜",
    ],
    "beija": [
        "*dá um beijo de caveira em {alvo}* mwah!! cuidado com os dentinhos!! 💀😘",
        "*beija {alvo} de leve* 💀💋",
        "*manda um beijo voando de longe pra {alvo}* mwaa!! 🦴💋",
    ],
    "chuta": [
        "*dá um chutinho de osso em {alvo}* toma!! 🦴💥",
        "*chuta {alvo} com a canela de osso* PLOFT!! 💀🦴",
        "*chuta e o próprio pé de osso sai voando junto* ops, foi sem querer!! 💀😂",
    ],
    "ataca": [
        "*avança sobre {alvo} chacoalhando os ossos* ATAQUEEE!! 💀⚔️",
        "*pula em cima de {alvo}* rá, se ferrou!! 🦴😈",
        "*investe contra {alvo} com tudo* CRACK CRACK!! 💀🦴",
        "*ataca fazendo pose dramática antes* preparem-se... CRACK!! 💀⚔️",
    ],
    "cutuca": [
        "*cutuca {alvo} com o dedinho de osso* toc toc!! 🦴👀",
        "*fica cutucando {alvo} sem parar* toc toc toc!! 💀😆",
        "*cutuca e sai correndo rindo* pega eu!! kkkk 🦴💨",
    ],
    "belisca": [
        "*belisca {alvo} de leve* ai, mentira, eu nem tenho carne pra beliscar!! kkkk 💀🦴",
        "*tenta beliscar mas só bate osso no osso* clack, isso doeu em mim!! 💀😆",
    ],
    "empurra": [
        "*empurra {alvo} de leve* opa, sai da frente!! 🦴😆",
        "*dá um empurrãozinho em {alvo}* eita, com força não!! 💀",
        "*empurra e quase perde o próprio equilíbrio* eita, casa de osso é osso!! 🦴😅",
    ],
    "ignora": [
        "*vira a caveira pro outro lado, ignorando {alvo}* 💀🙄",
        "*finge que não viu {alvo}* ... 👀💀",
        "*assobia baixinho fingindo que não é com ele* cracc... cracc... 💀",
    ],
    "acorda": [
        "*abre um olho da órbita vazia* hm?? já?? tá bom, acordei!! 😴💀",
        "*se espreguiça todo desconjuntado* ain, {alvo}, deixa eu dormir mais um pouco!! 💀😴",
        "*acorda de sobressalto e um osso cai no chão* eu tô bem, eu tô bem!! 🦴😵",
    ],
    "chama": [
        "*aparece flutuando na hora* presente!! quem chamou?? 💀🦴",
        "*surge de trás de {alvo}* falou meu nome?? 👀💀",
    ],
    "bate": [
        "*leva a batida e os ossos chacoalham todos* AI!! (bom, sou só osso, não dói tanto) 💀😂",
        "*os ossos tremem com o baque* CLACK!! ok isso eu senti!! 🦴😳",
    ],
    "assusta": [
        "*se assusta e os ossinhos voam pro alto* AAAAH!! 😱💀🦴",
        "*pula de susto, quase se desmonta* eita, {alvo}, quase me tirou um osso do lugar!! 💀😱",
        "*dá um salto pra trás e a caveira quase cai* AAAAAH NÃO FAZ ISSO!! 😱🦴",
        "*congela no lugar, os ossinhos travados de susto* ...vocês viram isso?? eu quase morri (de novo) 💀😰",
        "*solta um gritinho estridente e se esconde detrás de um osso* SOCORRO... ah espera, já passou 😱💀",
    ],
    "rouba": [
        "*esconde os ossinhos rapidinho* ei, isso é meu, {alvo}!! 🦴😤",
        "*sai correndo com o que restou dos ossos* NÃOOO devolve!! 🦴💨",
    ],
    "brinca": [
        "*sacode animado, pronto pra brincar* eba, bora brincar!! 🦴✨",
        "*rodopia de felicidade* brincadeira?? eu topo sempre!! 💀🎉",
    ],
    "foge": [
        "*sai flutuando rapidinho, os ossos voando pra trás* AAAH TCHAU!! 👻💀",
        "*foge de {alvo} chacoalhando todo* CRACK CRACK CORRE!! 🦴💨",
        "*desaparece numa nuvem de poeira de osso* nem me viram sair!! 👻🦴",
    ],
    "protege": [
        "*se põe na frente de {alvo}, escudo de osso ativado* pode vir, eu seguro!! 🦴🛡️",
        "*abre os braços protegendo {alvo}* passa por cima de mim primeiro!! 💀🛡️",
    ],
    "cura": [
        "*balança os ossinhos numa dancinha mágica em cima de {alvo}* fica bom logo!! 🦴✨💫",
        "*sopra uma poeira de osso reluzente em {alvo}* pronto, remédio de caveira!! 💀✨",
    ],
    "grita": [
        "*se encolhe todo com o grito* AAAI meus tímpanos (que eu não tenho)!! 😱💀",
        "*os ossos chacoalham em resposta ao grito* opa, calma, calma!! 🦴😅",
    ],
    "berra": [
        "*se assusta com o berro e derruba um osso* eita, grita não que eu me desmonto!! 😱🦴",
    ],
    "sussurra": [
        "*se aproxima flutuando de mansinho pra escutar* hm?? fala baixinho de novo, quase não ouço sem orelha 👂💀",
        "*inclina a caveira pra ouvir melhor* segredo?? conta, conta!! 🤫💀",
    ],
    "dança": [
        "*rebola os ossinhos desengonçado* dancinha de caveira ativada!! 💀🕺",
        "*tenta acompanhar o ritmo e quase se desmonta* isso aqui é osso solto, literalmente!! 🦴💃",
    ],
    "canta": [
        "*acompanha cantando com uma voz que só sai ecoando* laaaa lá lá (é osso cantando, relevem)!! 🦴🎶",
    ],
    "chora": [
        "*fica sem graça vendo {alvo} chorar e se aproxima* ei, ei, tá tudo bem?? tô aqui!! 🦴💔",
        "*envolve {alvo} num abraço consolador* pode chorar, eu seguro os ossinhos por você 💀🥺",
    ],
    "ri": [
        "*ri junto, os dentinhos batendo* kkkkk cracc cracc!! 💀😂",
    ],
    "persegue": [
        "*sai flutuando atrás de {alvo} sem parar* voltaaa aqui!! kkkk 🦴💨",
    ],
    "consola": [
        "*pousa a mãozinha de osso no ombro de {alvo}* tô aqui, ossinho(a)!! vai ficar tudo bem 🦴🤍",
    ],
    "zoa": [
        "*ri baixinho e desvia* ei, poupa, eu sou só um monte de osso indefeso!! 💀😆",
    ],
    "fotografa": [
        "*faz pose toda desengonçada pra foto* tira meu lado bom (eu só tenho ossos, então qualquer lado serve) 📸💀",
    ],
    "acaricia": [
        "*se derrete (osso não derrete mas relevem) com o carinho* aaaah que gostoso, faz de novo 🥹💀",
    ],
    "voa": [
        "*sai flutuando em espiral pelo ar* eu já flutuo o tempo todo mas tá bom, vamos voar!! 🦴✈️",
    ],
}

# Verbos que quando combinados com "bones" tendem a gerar um susto —
# usados também fora do RP, quando alguém tenta assustar o Bones
# escrevendo "bu", "buu" etc.
_GATILHOS_SUSTO = ["bu", "buu", "buuu", "aaah", "aaaah"]
_RESPOSTAS_SUSTO = [
    "AAAAAH!! *os ossinhos voam em todas as direções* 😱💀🦴",
    "*pula pra trás assustado, quase caindo em pedaços* NÃO FAZ ISSO, EU SOU FRÁGIL (literalmente feito de osso)!! 😱🦴",
    "*congela por um segundo, depois relaxa* ...quase, quase me pegou dessa vez!! 💀😅",
    "*deixa a caveira cair de susto e corre pra recolocar* eita, essa foi por pouco!! 🦴😳",
    "*solta um gritinho fino e se esconde detrás de alguém* SOCORROOO... ah, era você. oi 💀😆",
]
for _g in _GATILHOS_SUSTO:
    _RESPOSTAS_SEED[_g] = list(_RESPOSTAS_SUSTO)

# Reações genéricas pra qualquer verbo que não esteja no dicionário acima —
# assim o Bones sempre reage a uma ação, mesmo que não reconheça o verbo.
_REACOES_RP_GENERICA = [
    "*entra na brincadeira mesmo sem entender direito a ação* 💀✨",
    "*balança os ossinhos, participando da cena* 🦴😄",
    "*reage do jeito que dá, sendo só um monte de osso* 💀🦴",
    "*se mexe desengonçado tentando acompanhar* 🦴😅",
    "*inclina a caveira, meio confuso, mas topa* tá, vamo nessa!! 💀🤷",
    "*imita o gesto sem saber muito bem o que é* isso mesmo?? assim?? 🦴😆",
    "*chacoalha os ossos animado, participando de qualquer jeito* 💀🎉",
    "*faz uma cara de osso confuso* eu não sei o que isso significa mas eu topo!! 🦴😳",
]

# Reconhece mensagens no formato "Bones <verbo> <resto>" (RP de ação)
_PADRAO_ACAO_RP = re.compile(r"^bones\s+(\S+)\s*(.*)$", re.IGNORECASE)

# Reconhece também o formato "me <verbo>" — ex.: "me abraça", "me morde".
# Isso cobre quem responde direto pro Bones (reply/menção) sem precisar
# escrever "Bones" antes do verbo.
_PADRAO_ACAO_RP_ME = re.compile(r"^me\s+(\S+)\s*(.*)$", re.IGNORECASE)

# ══════════════════════════════════════════════════════════════════
#  🌫️  EXPRESSÕES ESPONTÂNEAS (aparece do nada, sem ser chamado)
# ══════════════════════════════════════════════════════════════════

_EXPRESSOES_ESPONTANEAS = [
    "*os ossinhos tremem sozinhos no canto* 🦴",
    "clack... clack... 💀",
    "*flutua devagar pelo canal e some* 👻",
    "*espia por trás de uma mensagem antiga* 👀💀",
    "tlim... um ossinho caiu em algum lugar 🦴✨",
    "*se remonta depois de cair no chão* 💀🦴",
    "cracc cracc cracc... 💀",
    "*observa em silêncio, balançando a mandíbula* 💀",
    "*se esconde de novo no escuro* 👻🦴",
    "psiu... o Bones tá de olho 👀💀",
    # variações com clima de susto — Bones pregando peça no chat
    "*surge bem no meio da tela sem avisar* BU!! ...ok já vou de novo 😱👻",
    "*aparece de repente atrás de todo mundo* será que alguém sentiu minha presença?? 👀💀",
    "*faz barulho de osso quicando no escuro* clack... CLACK... alguém aí?? 🦴👻",
    # voz sonolenta flutuando de madrugada
    "*flutua bocejando, meio zumbi* uuuh... que horas são... 😴💀",
    # voz hiperativa aparecendo
    "OIEE EU TÔ AQUI DE NOVO!! *dá cambalhotas no ar* 🦴⚡",
    # gíria/informal
    "só passando pra dar um alô pro pessoal, gente boa 🦴😎",
    # sussurro misterioso
    "*sussurra baixinho vindo do nada* alguém... me... chamou...?? 🤫👻",
]

# ══════════════════════════════════════════════════════════════════
#  🦴  PIADAS DE OSSOS (o Bones solta uma de vez em quando)
# ══════════════════════════════════════════════════════════════════

# Chance de, numa aparição espontânea, soltar uma piada em vez de
# uma expressão comum (ex.: 0.4 = 40% das aparições viram piada)
CHANCE_PIADA_NA_APARICAO = 0.4

_PIADAS_OSSOS = [
    "sabe por que se deve contratar um esqueleto?? porque ele conhece os ossos do ofício!! 💀🦴 kkkkk",
    "qual é o golpe favorito dos esqueletos?? um osso-soco!! 🦴💀",
    "por que o esqueleto não brigou com ninguém?? porque ele não tem estômago pra isso!! 💀😂",
    "por que o esqueleto não vai a festas?? porque ele não tem corpo pra dançar!! 🦴✨",
    "o que um osso disse pro outro osso?? \"a gente se encaixa direitinho\"!! 💀🦴",
    "por que o esqueleto ficou sozinho?? porque ele não tinha ninguém ao seu lado (literalmente, faltava a costela)!! 💀😆",
    "sabe qual o instrumento favorito do esqueleto?? o trom-bone!! 🦴🎺",
    "por que o esqueleto foi mal na prova?? porque ele só tinha os ossos do conhecimento!! 💀📚",
    "o que o esqueleto disse quando ganhou na loteria?? \"agora eu tô rico até a medula\"!! 🦴💰",
    "por que os esqueletos não discutem?? porque eles não têm estômago pra confusão!! 💀🦴",
    "qual o hobby favorito do esqueleto?? tocar tromBONE e colecionar OSSOgrafias!! 🦴🎶",
    "por que o esqueleto foi no médico?? pra fazer um check-up nos ossos do ofício de novo!! 💀🩻 kkkkk",
    "sabe o que o esqueleto fala quando alguém erra?? \"relaxa, isso não é osso duro de roer\"!! 🦴😂",
    "por que o esqueleto não empresta dinheiro?? porque ele já tá liso até os ossos!! 💀💸",
    "por que o esqueleto foi rejeitado no encontro?? porque ele não tinha coração pra dar!! 🦴💔",
    "qual é o esporte favorito do esqueleto?? boliche, ele já é todo osso e ainda derruba os pinos!! 💀🎳",
    "por que o esqueleto ficou de boa na praia?? porque ele já tá com o corpo sequinho!! 🦴🏖️ kkkk",
    "o que o esqueleto disse pro dentista?? \"pode ir com calma, eu não tenho nervosismo, só nervos mesmo\"!! 💀🦷",
]

# Também funciona como gatilho de diálogo comum — assim "Bones conte uma
# piada", "fala uma piada", "manda uma piada" etc. tudo cai aqui, não só
# o comando b!piada. Cadastra várias formas diferentes de pedir, porque
# a galera não fala tudo igual — cada frase abaixo é um jeito diferente
# de pedir a mesma coisa, e todas puxam do mesmo pool de piadas.
_RESPOSTAS_SEED["piada"] = list(_PIADAS_OSSOS)
for _frase_piada in (
    "conte uma piada",
    "conta uma piada",
    "me conte uma piada",
    "me conta uma piada",
    "fala uma piada",
    "me fala uma piada",
    "manda uma piada",
    "solta uma piada",
    "diz uma piada",
    "diga uma piada",
    "quero uma piada",
    "sabe uma piada",
    "tem uma piada",
    "conta ai uma piada",
    "conta aí uma piada",
    "piada de osso",
    "piada de ossos",
    "piada de esqueleto",
    "me conte uma piada bones",
):
    _RESPOSTAS_SEED[_frase_piada] = list(_PIADAS_OSSOS)

# ══════════════════════════════════════════════════════════════════
#  🖼️  HELPERS DE EMBED
# ══════════════════════════════════════════════════════════════════

def _embed_ok(titulo: str, desc: str) -> discord.Embed:
    e = discord.Embed(title=titulo, description=desc, color=COR_VERDE, timestamp=datetime.now(timezone.utc))
    e.set_footer(text=f"💀 Bones • {SERVER_TAG}")
    return e


def _embed_erro(desc: str) -> discord.Embed:
    e = discord.Embed(title="❌ eita!!", description=desc, color=COR_VERMELHO, timestamp=datetime.now(timezone.utc))
    e.set_footer(text=f"💀 Bones • {SERVER_TAG}")
    return e


def _embed_info(titulo: str, desc: str) -> discord.Embed:
    e = discord.Embed(title=titulo, description=desc, color=COR_ROXA, timestamp=datetime.now(timezone.utc))
    e.set_footer(text=f"💀 Bones • {SERVER_TAG}")
    return e


# ══════════════════════════════════════════════════════════════════
#  💬  COG DE DIÁLOGO — o coração do "aparece do nada"
# ══════════════════════════════════════════════════════════════════

class BonesDialogoCog(commands.Cog, name="BonesDialogo"):
    """💀 Sistema de interação, aprendizado e aparições espontâneas do Bones."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = _carregar_dialogo()

        # Mescla o vocabulário seed com o que já foi ensinado antes
        for chave, resps in _RESPOSTAS_SEED.items():
            if chave not in self.db["respostas"]:
                self.db["respostas"][chave] = resps
        _salvar_dialogo(self.db)

        # Cooldown de resposta por canal
        self._ultimo_resp: dict[int, datetime] = {}
        # Última vez que alguém interagiu diretamente com o Bones em cada canal
        # (gatilho respondido ou menção) — usado pra saber se o canal tá "engajado"
        self._ultima_interacao: dict[int, datetime] = {}

    # ── Helpers internos ──────────────────────────────

    def _checar_gatilho(self, texto: str) -> str | None:
        texto_lower = texto.lower().strip()
        if texto_lower in self.db["respostas"]:
            return texto_lower

        # Junta todos os gatilhos que aparecem na frase, e prioriza o mais
        # específico: mais palavras primeiro, depois mais caracteres.
        # Isso resolve casos tipo "conte uma piada bones" — antes o
        # gatilho "bones" (só por estar sendo chamado) roubava a resposta
        # de "piada" no empate de tamanho de string.
        candidatos = [c for c in self.db["respostas"] if c in texto_lower]
        if not candidatos:
            return None
        candidatos.sort(key=lambda c: (len(c.split()), len(c)), reverse=True)

        # "bones" (o próprio nome/chamado) nunca vence se existir outro
        # gatilho mais específico junto na mesma frase — ele só responde
        # "presente!!" quando for realmente a única coisa detectada.
        if candidatos[0] == "bones" and len(candidatos) > 1:
            return candidatos[1]
        return candidatos[0]

    def _responder(self, chave: str) -> str:
        resps = self.db["respostas"].get(chave, [])
        return random.choice(resps) if resps else ""

    def _em_cooldown(self, channel_id: int, now: datetime) -> bool:
        ultimo = self._ultimo_resp.get(channel_id)
        return bool(ultimo and (now - ultimo).total_seconds() < COOLDOWN_RESPOSTA)

    def _detectar_reacao_rp(self, texto: str) -> str | None:
        """Detecta ações de RP em três formatos:
        • 'Bones <verbo> <alvo>'  — ex.: "Bones morde o vilão"
        • 'me <verbo>'            — ex.: "me abraça" (pede a ação pra si
          mesmo, sem precisar chamar "Bones" antes — comum em replies)
        • verbo isolado           — ex.: responder só "abraça" numa
          conversa direta com o Bones
        Nos dois últimos casos o alvo é sempre "você" (quem escreveu).
        """
        texto_limpo = texto.strip()

        m = _PADRAO_ACAO_RP.match(texto_limpo)
        if m:
            verbo = m.group(1).lower().strip(".,!?*")
            alvo = m.group(2).strip(" .,!?*") or "você"
            pool = _REACOES_RP.get(verbo, _REACOES_RP_GENERICA)
            return random.choice(pool).format(alvo=alvo)

        m2 = _PADRAO_ACAO_RP_ME.match(texto_limpo)
        if m2:
            verbo = m2.group(1).lower().strip(".,!?*")
            pool = _REACOES_RP.get(verbo, _REACOES_RP_GENERICA)
            return random.choice(pool).format(alvo="você")

        # Verbo isolado só conta se já for um verbo conhecido, pra não
        # transformar qualquer palavra solta numa ação aleatória.
        verbo_isolado = texto_limpo.lower().strip(".,!?*")
        if verbo_isolado in _REACOES_RP:
            return random.choice(_REACOES_RP[verbo_isolado]).format(alvo="você")

        return None

    # ── Evento principal: aqui o Bones "vive" no chat ──

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return  # é um comando, não entra no diálogo

        now = datetime.now(timezone.utc)
        if self._em_cooldown(message.channel.id, now):
            return

        # Menção "de verdade": a pessoa digitou @Bones (aparece como
        # <@id> no conteúdo cru) ou escreveu "bones" no texto. Isso é
        # diferente de "self.bot.user in message.mentions", que também
        # fica True quando alguém só dá reply numa mensagem do Bones
        # (o Discord conta o ping automático do reply como menção) —
        # e a galera reclamou que isso fazia ele "chamar a si mesmo"
        # mesmo quando só estavam respondendo sem querer chamar.
        mencao_explicita = bool(re.search(rf"<@!?{self.bot.user.id}>", message.content))
        bones_mencionado = (
            mencao_explicita
            or "bones" in message.content.lower()
        )

        chave = self._checar_gatilho(message.content)

        # Detecta se a mensagem é uma ação de RP ("Bones morde o vilão",
        # "Bones abraça a galera" etc.). Isso tem prioridade sobre o
        # gatilho genérico "bones" — antes, qualquer ação de RP virava só
        # um "presente!!" porque a palavra "bones" também é um gatilho e
        # sempre "ganhava" primeiro. Agora a ação real é priorizada.
        reacao_rp = self._detectar_reacao_rp(message.content) if bones_mencionado else None
        if reacao_rp and chave == "bones":
            chave = None

        # ── 1) Gatilho conhecido: só responde quando o Bones foi
        #        de fato chamado (mencionado ou em reply) ─────────
        if chave and bones_mencionado:
            resp = self._responder(chave)

            # Reconhecimento especial: se for a pessoa especial e o
            # gatilho for do tema "esposa", às vezes (não sempre) o
            # Bones retribui com algo mais pessoal em vez da resposta
            # genérica do gatilho.
            if (
                message.author.id == USUARIO_ESPECIAL_ID
                and chave in _GATILHOS_ESPOSA
                and random.random() < CHANCE_RECONHECER_ESPECIAL
            ):
                resp = random.choice(_RESPOSTAS_ESPOSA_ESPECIAL)

            if resp:
                self._ultimo_resp[message.channel.id] = now
                self._ultima_interacao[message.channel.id] = now
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(0.8, 1.8))
                await message.reply(resp, mention_author=False)
                return

        # ── 2) Foi chamado mas sem gatilho específico (ou virou uma
        #        ação de RP que acabou de ganhar prioridade acima) ────
        if bones_mencionado and not chave:
            self._ultimo_resp[message.channel.id] = now
            self._ultima_interacao[message.channel.id] = now
            async with message.channel.typing():
                await asyncio.sleep(random.uniform(0.5, 1.2))

            if reacao_rp:
                await message.reply(reacao_rp, mention_author=False)
            elif (
                message.author.id == USUARIO_ESPECIAL_ID
                and random.random() < CHANCE_RECONHECER_ESPECIAL
            ):
                # Reconhecimento especial fora do tema "esposa": de vez
                # em quando o Bones puxa algo mais pessoal só pra ela,
                # não é sempre, pra não ficar repetitivo.
                await message.reply(random.choice(_RESPOSTAS_MENCAO_ESPECIAL), mention_author=False)
            else:
                await message.reply(random.choice(_RESPOSTAS_MENCAO), mention_author=False)
            return

        # ── 3) Ninguém chamou, sem gatilho: chance de o Bones
        #        "aparecer do nada" de forma espontânea. A chance sobe
        #        se o canal teve interação direta com ele há pouco tempo,
        #        e o intervalo mínimo entre aparições varia (não é fixo). ─
        if not bones_mencionado and not chave:
            ultima_int = self._ultima_interacao.get(message.channel.id)
            engajado = bool(ultima_int and (now - ultima_int).total_seconds() < JANELA_ENGAJAMENTO)
            chance = CHANCE_ESPONTANEA_ENGAJADO if engajado else CHANCE_ESPONTANEA_BASE

            if random.random() < chance:
                ultimo = self._ultimo_resp.get(message.channel.id)
                cooldown_sorteado = random.uniform(COOLDOWN_ESPONTANEA_MIN, COOLDOWN_ESPONTANEA_MAX)
                if not ultimo or (now - ultimo).total_seconds() > cooldown_sorteado:
                    self._ultimo_resp[message.channel.id] = now
                    async with message.channel.typing():
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                    if random.random() < CHANCE_PIADA_NA_APARICAO:
                        await message.channel.send(random.choice(_PIADAS_OSSOS))
                    else:
                        await message.channel.send(random.choice(_EXPRESSOES_ESPONTANEAS))

    # ── Comandos de aprendizado ────────────────────────

    @commands.command(name="ensinar", aliases=["teach"])
    @commands.has_permissions(manage_messages=True)
    async def ensinar(self, ctx: commands.Context, gatilho: str, *, resposta: str):
        """Ensina o Bones uma nova resposta. Uso: b!ensinar <gatilho> <resposta>"""
        chave = gatilho.lower().strip()
        self.db["respostas"].setdefault(chave, [])
        if resposta in self.db["respostas"][chave]:
            await ctx.send(embed=_embed_erro(f"o Bones já sabe responder **{resposta}** pro gatilho `{chave}`!! 💀"))
            return
        self.db["respostas"][chave].append(resposta)
        _salvar_dialogo(self.db)
        await ctx.send(embed=_embed_ok(
            "🦴 Aprendido!!",
            f"o Bones agora responde `{chave}` com:\n> {resposta}"
        ))

    @commands.command(name="esquecer", aliases=["forget"])
    @commands.has_permissions(manage_messages=True)
    async def esquecer(self, ctx: commands.Context, *, gatilho: str):
        """Remove todas as respostas de um gatilho. Uso: b!esquecer <gatilho>"""
        chave = gatilho.lower().strip()
        if chave not in self.db["respostas"]:
            await ctx.send(embed=_embed_erro(f"o Bones não conhece o gatilho `{chave}`!! 💀"))
            return
        del self.db["respostas"][chave]
        _salvar_dialogo(self.db)
        await ctx.send(embed=_embed_ok("🦴 Esquecido!!", f"o Bones esqueceu tudo sobre `{chave}`!! 💀"))

    @commands.command(name="gatilhos", aliases=["triggers"])
    async def gatilhos(self, ctx: commands.Context):
        """Lista todos os gatilhos que o Bones conhece."""
        chaves = sorted(self.db["respostas"].keys())
        if not chaves:
            await ctx.send(embed=_embed_info("🦴 Gatilhos", "o Bones ainda não aprendeu nada!! 💀"))
            return
        desc = ", ".join(f"`{c}`" for c in chaves)
        await ctx.send(embed=_embed_info("🦴 Gatilhos que o Bones conhece", desc))

    @commands.command(name="resposta", aliases=["responses"])
    async def resposta(self, ctx: commands.Context, *, gatilho: str):
        """Mostra as respostas cadastradas para um gatilho."""
        chave = gatilho.lower().strip()
        resps = self.db["respostas"].get(chave)
        if not resps:
            await ctx.send(embed=_embed_erro(f"o Bones não conhece o gatilho `{chave}`!! 💀"))
            return
        desc = "\n".join(f"• {r}" for r in resps)
        await ctx.send(embed=_embed_info(f"🦴 Respostas para `{chave}`", desc))

    @commands.command(name="simular", aliases=["simulate"])
    async def simular(self, ctx: commands.Context, *, texto: str):
        """Testa o que o Bones responderia a um texto. Uso: b!simular <texto>"""
        chave = self._checar_gatilho(texto)
        if not chave:
            await ctx.send(embed=_embed_info("🦴 Simulação", "o Bones ficaria só flutuando em silêncio... nenhum gatilho encontrado!! 👻"))
            return
        resp = self._responder(chave)
        await ctx.send(embed=_embed_info("🦴 Simulação", f"gatilho: `{chave}`\nresposta: {resp}"))

    @commands.command(name="piada", aliases=["joke", "piadinha"])
    async def piada(self, ctx: commands.Context):
        """Solta uma piada de ossos na hora. Uso: b!piada"""
        async with ctx.channel.typing():
            await asyncio.sleep(random.uniform(0.5, 1.0))
        await ctx.send(random.choice(_PIADAS_OSSOS))



# ══════════════════════════════════════════════════════════════════
#  💀  EVENTOS GLOBAIS DO BOT
# ══════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print(f"\n{'═'*52}")
    print("  💀  BONES BOT — ONLINE")
    print(f"  Logado como: {bot.user} ({bot.user.id})")
    print(f"  Servidores: {len(bot.guilds)}")
    print(f"{'═'*52}\n")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"os ossinhos da {SERVER_TAG} 💀🦴"
        )
    )


# ══════════════════════════════════════════════════════════════════
#  📋  COMANDOS GERAIS
# ══════════════════════════════════════════════════════════════════

@bot.command(name="help", aliases=["ajuda", "h"])
async def bones_help(ctx: commands.Context):
    embed = discord.Embed(
        title="💀 Bones — Ajuda",
        description=f"oi!! sou o Bones, a caveirinha fofa da {SERVER_TAG}!! 🦴✨\naqui tá tudo que eu sei fazer!!",
        color=COR_ROXA,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(
        name="💬 Diálogo & Interações",
        inline=False,
        value=(
            "eu apareço sozinho de vez em quando, respondo se me chamarem "
            "pelo nome e aprendo gatilhos novos!! 💀\n\n"
            "`b!ensinar <gatilho> <resposta>` — me ensina algo novo\n"
            "`b!esquecer <gatilho>` — apaga o que eu sei sobre um gatilho\n"
            "`b!gatilhos` — lista tudo que eu já aprendi\n"
            "`b!resposta <gatilho>` — mostra as respostas de um gatilho\n"
            "`b!simular <texto>` — testa o que eu responderia"
        )
    )
    embed.add_field(
        name="🦴 Geral",
        inline=False,
        value=(
            "`b!bones` — sobre mim\n"
            "`b!piada` — solto uma piada de ossos na hora\n"
            "`b!ping` — testa minha latência"
        )
    )
    embed.set_footer(text=f"💀 Bones • prefixo: b! ou bones ")
    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    latencia = round(bot.latency * 1000)
    cor = COR_VERDE if latencia < 100 else (COR_DOURADO if latencia < 200 else COR_VERMELHO)
    await ctx.send(embed=discord.Embed(
        title="🏓 Pong!!",
        description=f"latência: `{latencia}ms` 💀🦴",
        color=cor
    ))


@bot.command(name="bones")
async def bones_info(ctx: commands.Context):
    embed = discord.Embed(
        title="🦴 Oi!! Sou o Bones!!",
        description=(
            f"a caveirinha fofa da {SERVER_TAG} 💀✨\n\n"
            "gosto de aparecer do nada, bater um papo e aprender coisas novas "
            "com a galera!! não se assusta não, sou só ossinho e carinho 💀🦴\n\n"
            "usa `b!help` pra ver tudo que eu sei fazer!!"
        ),
        color=COR_ROXA,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="💀 Bones Bot v1.0")
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════
#  🚀  INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════════

async def _main():
    async with bot:
        await bot.add_cog(BonesDialogoCog(bot))

        if not TOKEN:
            print("❌ ERRO: token não encontrado! Crie um .env com BONES_TOKEN=seu_token")
            return
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(_main())
