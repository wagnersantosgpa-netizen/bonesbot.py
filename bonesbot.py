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
}

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
#  🎞️  GIFS DO BONES
#      Usados quando alguém pede um gif ou quando rola um gif no chat
#      (aí o Bones entra na brincadeira com um dele também).
#
#      OBS: antes essa lista usava links do tipo
#      "encrypted-tbn0.gstatic.com/images?q=tbn:..." — esses são links
#      de MINIATURA do cache de imagens do Google, não do gif de
#      verdade. Por isso apareciam estáticos: nunca foram um gif
#      animado, sempre foram uma fotinho estática do resultado de
#      busca. Trocado por links de página do Tenor (tenor.com/view/...),
#      que o Discord reconhece e renderiza como gif animado de verdade.
# ══════════════════════════════════════════════════════════════════

_GIFS_BONES = [
    "https://tenor.com/en-GB/view/skeleton-dance-dancing-gif-10430058",
    "https://tenor.com/view/skeleton-dancing-cartoon-skeletons-gif-5474567",
    "https://tenor.com/view/skeleton-dancing-dance-turn-up-lit-gif-5623073",
    "https://tenor.com/view/dancing-skeleton-gif-9517238",
    "https://tenor.com/view/skeleton-dancing-animation-gif-7794277",
    "https://tenor.com/view/skeleton-dancing-skeleton-dancing-gif-5094083",
    "https://tenor.com/view/skeleton-dance-fast-gif-23242269",
    "https://tenor.com/view/skeleton-dance-skeleton-skeleton-dancing-skeleton-meme-smiling-friends-gif-9010165550533699083",
]

_RESPOSTAS_GIF = [
    "toma um gif, ossinho(a)!! 🦴🎞️",
    "*flutua e solta um gif do nada* 💀🎬",
    "gif liberado!! aqui óh 🦴✨",
    "peguei um da minha coleção de ossos... quer dizer, de gifs 💀😆",
    "clack clack!! segue o gif 🦴🎞️",
    "entrando na moda dos gifs também!! 💀🎬",
    "*procura na gaveta de ossos e acha um gif* achei um!! 🦴💀",
]

# Quando ninguém chamou o Bones mas alguém posta/pede um gif no chat,
# ele tem uma chance de "reagir" entrando na brincadeira com um gif
# dele também — não é sempre, senão vira spam. Se ele FOR chamado
# (@Bones ou "bones" no texto), a reação é sempre garantida.
CHANCE_REACAO_GIF = 0.25       # chance por gif/pedido, sem ser chamado
COOLDOWN_REACAO_GIF = 20       # (segundos) intervalo mínimo entre reações a gif no mesmo canal

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
        # Última vez que o Bones reagiu com um gif em cada canal (evita
        # ele jogar gif toda hora quando ninguém chamou ele diretamente)
        self._ultima_reacao_gif: dict[int, datetime] = {}

    # ── Helpers internos ──────────────────────────────

    def _contem_gif(self, message: discord.Message) -> bool:
        """Verifica se a mensagem 'tem a ver com gif' — seja um gif de
        verdade anexado/linkado, seja só a palavra 'gif' escrita (um
        pedido, tipo 'bones manda um gif')."""
        for anexo in message.attachments:
            if anexo.filename.lower().endswith(".gif") or (
                anexo.content_type and "gif" in anexo.content_type
            ):
                return True
        texto = message.content.lower()
        return "gif" in texto or "tenor.com" in texto or "giphy.com" in texto

    def _pode_reagir_gif(self, channel_id: int, now: datetime) -> bool:
        """Decide se o Bones reage a um gif quando NÃO foi chamado —
        chance + cooldown, pra não virar spam de gif no canal."""
        if random.random() >= CHANCE_REACAO_GIF:
            return False
        ultima = self._ultima_reacao_gif.get(channel_id)
        return not ultima or (now - ultima).total_seconds() > COOLDOWN_REACAO_GIF

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

        # ── 0) Conta solta no meio da frase: "bones 1+1", "bones quanto
        #        é 5*3", "5-2 bones" etc. Isso tem prioridade máxima —
        #        se tem uma conta ali e o Bones foi chamado, ele calcula
        #        na hora, sem precisar de b!conta nem de gatilho. ──────
        if bones_mencionado:
            conta = _detectar_conta_no_texto(message.content)
            if conta:
                bruta, resultado = conta
                self._ultimo_resp[message.channel.id] = now
                self._ultima_interacao[message.channel.id] = now
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(0.5, 1.2))
                if resultado is _DIVISAO_POR_ZERO:
                    resp = random.choice(_RESPOSTAS_CONTA_ZERO).format(bruta=bruta)
                else:
                    if isinstance(resultado, float) and resultado.is_integer():
                        resultado = int(resultado)
                    resp = random.choice(_RESPOSTAS_CONTA_NATURAL).format(bruta=bruta, resultado=resultado)
                await message.reply(resp, mention_author=False)
                return

        # ── 0.5) Gif: alguém pediu um gif ("bones manda um gif") ou
        #        postou/linkou um gif no chat. Se o Bones foi chamado,
        #        ele SEMPRE entra na brincadeira; se não foi chamado,
        #        tem uma chance (+ cooldown) de reagir por conta própria,
        #        pra não virar spam de gif no canal toda hora. ─────────
        if self._contem_gif(message):
            reagir = bones_mencionado or self._pode_reagir_gif(message.channel.id, now)
            if reagir:
                self._ultimo_resp[message.channel.id] = now
                if bones_mencionado:
                    self._ultima_interacao[message.channel.id] = now
                else:
                    self._ultima_reacao_gif[message.channel.id] = now
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(0.4, 1.0))
                conteudo = f"{random.choice(_RESPOSTAS_GIF)}\n{random.choice(_GIFS_BONES)}"
                if bones_mencionado:
                    await message.reply(conteudo, mention_author=False)
                else:
                    await message.channel.send(conteudo)
                return

        # ── 0.7) Pergunta de conceito: "qual é a fórmula de baskara?",
        #        "o que é uma fração?", "explica porcentagem" etc. Se o
        #        assunto for algo que o Bones sabe explicar, ele responde
        #        de verdade em vez de cair na reação genérica de RP. ────
        if bones_mencionado:
            assunto = _extrair_assunto_pergunta(message.content)
            if assunto:
                explicacao = _buscar_explicacao(assunto)
                if explicacao:
                    self._ultimo_resp[message.channel.id] = now
                    self._ultima_interacao[message.channel.id] = now
                    async with message.channel.typing():
                        await asyncio.sleep(random.uniform(0.6, 1.4))
                    await message.reply(explicacao, mention_author=False)
                    return

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

    @commands.command(name="gif")
    async def gif(self, ctx: commands.Context):
        """Manda um gif aleatório do Bones. Uso: b!gif"""
        async with ctx.channel.typing():
            await asyncio.sleep(random.uniform(0.4, 1.0))
        await ctx.send(f"{random.choice(_RESPOSTAS_GIF)}\n{random.choice(_GIFS_BONES)}")



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
        name="🧮 Matemática",
        inline=False,
        value=(
            "aprendi conta também!! várias formas de aprender comigo 💀\n\n"
            "`b!conta <expressão>` — calculo na hora, tipo `b!conta (4+2)*3`\n"
            "`b!tabuada <número>` — mostro a tabuada completa\n"
            "`b!explicar <tópico>` — explico soma, fração, porcentagem etc.\n"
            "`b!quiz [facil|medio|dificil]` — te desafio com uma conta!!"
        )
    )
    embed.add_field(
        name="🦴 Geral",
        inline=False,
        value=(
            "`b!bones` — sobre mim\n"
            "`b!piada` — solto uma piada de ossos na hora\n"
            "`b!gif` — mando um gif aleatório meu\n"
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
#  🧮  MÓDULO DE MATEMÁTICA DO BONES
#      (calculadora, tabuada, quiz e explicações — várias formas
#       de "ensinar" matemática pro Bones e pra galera)
# ══════════════════════════════════════════════════════════════════

import ast
import operator

_OPERADORES_PERMITIDOS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _avaliar_expressao(expr: str) -> float:
    """Avalia uma expressão matemática com segurança, sem usar eval()."""

    def _eval(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return node.value
            raise ValueError("valor inválido")
        if isinstance(node, ast.BinOp):
            op_tipo = type(node.op)
            if op_tipo not in _OPERADORES_PERMITIDOS:
                raise ValueError("operador não suportado")
            return _OPERADORES_PERMITIDOS[op_tipo](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op_tipo = type(node.op)
            if op_tipo not in _OPERADORES_PERMITIDOS:
                raise ValueError("operador não suportado")
            return _OPERADORES_PERMITIDOS[op_tipo](_eval(node.operand))
        raise ValueError("expressão inválida")

    arvore = ast.parse(expr, mode="eval")
    return _eval(arvore.body)


# Reconhece uma conta solta em qualquer lugar da frase, tipo "bones 1+1"
# ou "quanto é 5*3 bones". Exige pelo menos um número, um operador e
# outro número — assim "top 10" ou um ID qualquer não vira conta à toa.
# Aceita x/X/× como multiplicação e ÷ como divisão, além de */+/-//.
_PADRAO_EXPRESSAO_MATEMATICA = re.compile(
    r"(?<![\w.,])(-?\d+(?:[.,]\d+)?(?:\s*[+\-xX×*/÷]\s*-?\d+(?:[.,]\d+)?)+)(?![\w.,])"
)


# Marcador especial pra dizer "essa conta tentou dividir por zero" sem
# precisar propagar a exceção lá pro on_message — assim dá pra tratar
# com uma fala engraçada em vez de só ignorar a mensagem.
_DIVISAO_POR_ZERO = object()


def _detectar_conta_no_texto(texto: str) -> tuple[str, float] | None:
    """Procura uma conta solta no meio da frase. Devolve (expressão
    original, resultado) ou None se não achar nada parecido com conta.
    Se a conta tentar dividir por zero, o resultado vem como
    _DIVISAO_POR_ZERO em vez de lançar exceção."""
    m = _PADRAO_EXPRESSAO_MATEMATICA.search(texto)
    if not m:
        return None
    bruta = m.group(1).strip()
    normalizada = bruta.replace("x", "*").replace("X", "*").replace("×", "*").replace("÷", "/")
    normalizada = re.sub(r"(\d),(\d)", r"\1.\2", normalizada)  # vírgula decimal → ponto
    try:
        resultado = _avaliar_expressao(normalizada)
    except ZeroDivisionError:
        return bruta, _DIVISAO_POR_ZERO
    except (ValueError, SyntaxError, TypeError):
        return None
    return bruta, resultado


# Várias falas diferentes pra quando o Bones calcula uma conta solta na
# conversa — assim ele não fica repetindo sempre o mesmo formato seco.
_RESPOSTAS_CONTA_NATURAL = [
    "*conta nos ossinhos dos dedos* `{bruta}`?? deixa eu ver... dá **{resultado}**!! 🦴💀",
    "clack clack!! `{bruta}` = **{resultado}**, ossinho(a)!! 🧮💀",
    "*flutua até o quadro-negro imaginário e escreve* `{bruta}` = **{resultado}**!! 💀✏️",
    "peraí, deixa eu usar os miolos... ah, esqueci que não tenho kkkk mas `{bruta}` dá **{resultado}**!! 🦴😆",
    "fácil!! `{bruta}` = **{resultado}** 💀🧮 quer outra conta??",
    "*balança a caveira concentrado* `{bruta}`... **{resultado}**!! acertei igual sempre 🦴✨",
    "opa, conta na área!! `{bruta}` = **{resultado}**, ossinho(a)!! 💀🦴",
    "*estala os dedos ósseos* na moral, `{bruta}` é **{resultado}**!! 🦴💀",
]

# Falas especiais pra quando alguém tenta fazer o Bones dividir por zero.
_RESPOSTAS_CONTA_ZERO = [
    "ei ei, `{bruta}`?? isso é dividir por zero!! nem os ossos aguentam essa 😱💀",
    "*os ossinhos tremem* dividir por zero não rola, ossinho(a)!! o universo (e o Bones) explode 💀💥",
    "kkkkk boa tentativa, mas `{bruta}` é impossível!! divisão por zero não existe por aqui 🦴🚫",
]


_EXPLICACOES_MATEMATICA = {
    "soma": (
        "➕ **Soma**\n"
        "é juntar quantidades!! tipo empilhar ossinhos: se eu tenho 3 e acho "
        "mais 2, fico com 5 no total!!\n`3 + 2 = 5` 🦴💀\n"
        "dica: dá pra somar em qualquer ordem, `3 + 2` é igual a `2 + 3`!!"
    ),
    "subtracao": (
        "➖ **Subtração**\n"
        "é tirar uma quantidade de outra. se eu tenho 5 ossinhos e perco 2, "
        "fico só com 3!!\n`5 - 2 = 3` 🦴💀\n"
        "dica: aqui a ordem importa! `5 - 2` não é igual a `2 - 5`!!"
    ),
    "multiplicacao": (
        "✖️ **Multiplicação**\n"
        "é somar a mesma quantidade várias vezes!! `4 × 3` é o mesmo que "
        "`4 + 4 + 4`, que dá 12!! 🦴💀\n"
        "dica: pensa em grupos! 3 grupos de 4 ossinhos cada!!"
    ),
    "divisao": (
        "➗ **Divisão**\n"
        "é repartir uma quantidade em partes iguais!! se eu tenho 12 ossinhos "
        "e quero dividir entre 3 amigos, cada um fica com 4!!\n`12 ÷ 3 = 4` 🦴💀"
    ),
    "fracao": (
        "🍕 **Fração**\n"
        "representa uma parte de um todo!! tipo `1/2` é metade de alguma "
        "coisa — se eu quebro um osso em 2 pedaços iguais e pego 1, tenho "
        "`1/2` do osso!! 🦴💀\no número de cima (numerador) diz quantas "
        "partes você tem, o de baixo (denominador) diz em quantas partes o "
        "todo foi dividido."
    ),
    "porcentagem": (
        "💯 **Porcentagem**\n"
        "é uma fração de 100!! `50%` é o mesmo que `50/100`, ou seja, "
        "metade!! 🦴💀\npra calcular X% de um número: `(X ÷ 100) × número`.\n"
        "ex: 20% de 50 = `(20 ÷ 100) × 50 = 10`"
    ),
    "area": (
        "📐 **Área**\n"
        "é o espaço que uma figura ocupa!! pra um retângulo: "
        "`área = largura × altura`. 🦴💀\n"
        "ex: um retângulo de 4 por 3 tem área `4 × 3 = 12`."
    ),
    "perimetro": (
        "📏 **Perímetro**\n"
        "é a soma de todos os lados de uma figura!! pra um retângulo: "
        "`perímetro = 2 × (largura + altura)`. 🦴💀"
    ),
    "potencia": (
        "🔺 **Potência**\n"
        "é multiplicar um número por ele mesmo várias vezes!! `2³` é "
        "`2 × 2 × 2 = 8`. o número de cima diz quantas vezes multiplicar!! 🦴💀"
    ),
    "raiz quadrada": (
        "√ **Raiz quadrada**\n"
        "é o oposto da potência!! `√9` pergunta \"que número vezes ele mesmo "
        "dá 9??\" — a resposta é 3, porque `3 × 3 = 9`!! 🦴💀"
    ),
    "bhaskara": (
        "📐 **Fórmula de Bhaskara**\n"
        "serve pra achar as raízes (os valores de x) de uma equação do "
        "segundo grau, tipo `ax² + bx + c = 0`!! 🦴💀\n"
        "primeiro calcula o discriminante: `Δ = b² - 4ac`\n"
        "depois: `x = (-b ± √Δ) / (2a)`\n"
        "dica: se `Δ` for negativo, a equação não tem raiz real!!"
    ),
    "regra de tres": (
        "🔢 **Regra de três**\n"
        "é um jeito de achar um valor desconhecido quando duas coisas são "
        "proporcionais!! tipo: se 2 ossos custam 10 moedas, quanto custam "
        "5 ossos?? monta assim:\n`2 --- 10`\n`5 --- x`\n"
        "multiplica cruzado: `x = (5 × 10) / 2 = 25` 🦴💀"
    ),
    "media": (
        "📊 **Média**\n"
        "soma todos os valores e divide pela quantidade deles!! tipo: a "
        "média de 4, 6 e 8 é `(4 + 6 + 8) / 3 = 6` 🦴💀"
    ),
    "mmc": (
        "🔢 **MMC (Mínimo Múltiplo Comum)**\n"
        "é o menor número que é múltiplo de dois ou mais números ao mesmo "
        "tempo!! ex: o MMC de 4 e 6 é 12, porque é o menor número que "
        "aparece nas duas tabuadas!! 🦴💀"
    ),
    "mdc": (
        "🔢 **MDC (Máximo Divisor Comum)**\n"
        "é o maior número que divide dois ou mais números sem deixar "
        "resto!! ex: o MDC de 8 e 12 é 4!! 🦴💀"
    ),
}
# aliases com acento apontando pro mesmo texto (aceita os dois jeitos de digitar)
_ALIASES_EXPLICACAO = {
    "subtração": "subtracao", "multiplicação": "multiplicacao",
    "divisão": "divisao", "fração": "fracao", "área": "area",
    "perímetro": "perimetro", "potência": "potencia",
    "baskara": "bhaskara", "formula de bhaskara": "bhaskara",
    "formula de baskara": "bhaskara", "fórmula de bhaskara": "bhaskara",
    "fórmula de baskara": "bhaskara", "regra de três": "regra de tres",
    "média": "media",
}
for _alias, _canonico in _ALIASES_EXPLICACAO.items():
    _EXPLICACOES_MATEMATICA[_alias] = _EXPLICACOES_MATEMATICA[_canonico]


# Padrões que reconhecem uma "pergunta de conceito" dentro da frase,
# tipo "qual é a fórmula de baskara?", "o que é uma fração?", "explica
# porcentagem". Cada padrão captura o assunto perguntado.
_PADROES_PERGUNTA_CONCEITO = [
    re.compile(r"f[oó]rmula\s+d[eo]\s+(.+)$"),
    re.compile(r"o\s+que\s+[eé]\s+(?:um[a]?\s+)?(.+)$"),
    re.compile(r"\bque\s+[eé]\s+(?:um[a]?\s+)?(.+)$"),
    re.compile(r"explic[ae]r?\s+(?:o\s+que\s+[eé]\s+)?(.+)$"),
    re.compile(r"como\s+funciona\s+(?:a|o)?\s*(.+)$"),
    re.compile(r"como\s+(?:eu\s+)?calcul[ao]\s+(?:a|o)?\s*(.+)$"),
]


def _extrair_assunto_pergunta(texto: str) -> str | None:
    """Tenta extrair o 'assunto' de uma pergunta conceitual solta na
    frase. Devolve o assunto (limpo, minúsculo) ou None se a frase não
    parecer esse tipo de pergunta."""
    t = texto.strip().rstrip("?!.").lower()
    for padrao in _PADROES_PERGUNTA_CONCEITO:
        m = padrao.search(t)
        if m:
            assunto = m.group(1).strip(" ?!.")
            assunto = re.sub(r"\bbones\b", "", assunto).strip()
            if assunto:
                return assunto
    return None


def _buscar_explicacao(assunto: str) -> str | None:
    """Procura a explicação de um assunto, com um fallback aproximado
    caso o texto tenha palavras extras junto do termo conhecido."""
    if assunto in _EXPLICACOES_MATEMATICA:
        return _EXPLICACOES_MATEMATICA[assunto]
    for chave, texto in _EXPLICACOES_MATEMATICA.items():
        if chave in assunto or assunto in chave:
            return texto
    return None


class BonesMatematicaCog(commands.Cog, name="BonesMatematica"):
    """🧮 Módulo de matemática do Bones — calculadora, tabuada, quiz e explicações."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="conta", aliases=["calcular", "calc"])
    async def conta(self, ctx: commands.Context, *, expressao: str):
        """Calcula uma expressão matemática. Uso: b!conta 2 + 2 * 5"""
        try:
            resultado = _avaliar_expressao(expressao)
            if isinstance(resultado, float) and resultado.is_integer():
                resultado = int(resultado)
            await ctx.send(embed=_embed_ok(
                "🧮 Conta feita!!",
                random.choice(_RESPOSTAS_CONTA_NATURAL).format(bruta=expressao, resultado=resultado)
            ))
        except ZeroDivisionError:
            await ctx.send(embed=_embed_erro(
                random.choice(_RESPOSTAS_CONTA_ZERO).format(bruta=expressao)
            ))
        except Exception:
            await ctx.send(embed=_embed_erro(
                "não consegui entender essa conta!! 💀\n"
                "usa só números e `+ - * / ** ( )`, tipo: `b!conta (4 + 2) * 3`"
            ))

    @commands.command(name="tabuada")
    async def tabuada(self, ctx: commands.Context, numero: int):
        """Mostra a tabuada de um número. Uso: b!tabuada 7"""
        if not (0 <= numero <= 100):
            await ctx.send(embed=_embed_erro("escolhe um número entre 0 e 100, ossinho(a)!! 💀"))
            return
        linhas = [f"{numero} × {i} = {numero * i}" for i in range(1, 11)]
        await ctx.send(embed=_embed_info(f"🦴 Tabuada do {numero}", "\n".join(linhas)))

    @commands.command(name="explicar", aliases=["explica"])
    async def explicar(self, ctx: commands.Context, *, topico: str):
        """Explica um conceito de matemática. Uso: b!explicar fração"""
        chave = topico.lower().strip()
        explicacao = _EXPLICACOES_MATEMATICA.get(chave)
        if not explicacao:
            disponiveis = ", ".join(f"`{k}`" for k in [
                "soma", "subtração", "multiplicação", "divisão", "fração",
                "porcentagem", "área", "perímetro", "potência"
            ])
            await ctx.send(embed=_embed_erro(
                f"ainda não sei explicar `{chave}`!! 💀\ntópicos que sei: {disponiveis}"
            ))
            return
        await ctx.send(embed=_embed_info("🧮 Aula do Bones", explicacao))

    @commands.command(name="quiz", aliases=["quizmath", "desafio"])
    async def quiz(self, ctx: commands.Context, dificuldade: str = "facil"):
        """Bones te desafia com uma conta pra resolver. Uso: b!quiz [facil|medio|dificil]"""
        dificuldade = dificuldade.lower().strip()
        faixas = {
            "facil": (1, 10, ["+", "-"]),
            "medio": (1, 50, ["+", "-", "*"]),
            "dificil": (2, 12, ["*", "/"]),
        }
        if dificuldade not in faixas:
            await ctx.send(embed=_embed_erro("dificuldade inválida!! usa `facil`, `medio` ou `dificil` 💀"))
            return

        minimo, maximo, ops = faixas[dificuldade]
        a = random.randint(minimo, maximo)
        b = random.randint(minimo, maximo)
        op = random.choice(ops)

        if op == "/":
            # garante divisão exata pra não complicar
            b = random.randint(2, 12)
            a = b * random.randint(2, 12)
            resultado = a // b
        elif op == "*":
            resultado = a * b
        elif op == "+":
            resultado = a + b
        else:
            if a < b:
                a, b = b, a
            resultado = a - b

        await ctx.send(embed=_embed_info(
            "🧮 Desafio do Bones!!",
            f"quanto é `{a} {op} {b}`??\nresponde aqui em até 20 segundos!! 💀🦴"
        ))

        def checar(m: discord.Message) -> bool:
            return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

        try:
            resposta_msg = await self.bot.wait_for("message", check=checar, timeout=20.0)
        except asyncio.TimeoutError:
            await ctx.send(embed=_embed_erro(f"o tempo acabou!! a resposta era **{resultado}** 💀⏰"))
            return

        try:
            valor_dado = float(resposta_msg.content.strip().replace(",", "."))
        except ValueError:
            await ctx.send(embed=_embed_erro(f"isso nem número é!! a resposta era **{resultado}** 💀"))
            return

        if valor_dado == resultado:
            await ctx.send(embed=_embed_ok(
                "🎉 Acertou!!", f"isso aí, ossinho(a)!! **{resultado}** tá certinho!! 🦴💀✨"
            ))
        else:
            await ctx.send(embed=_embed_erro(f"quase!! a resposta certa era **{resultado}** 💀"))


# ══════════════════════════════════════════════════════════════════
#  🚀  INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════════

async def _main():
    async with bot:
        await bot.add_cog(BonesDialogoCog(bot))
        await bot.add_cog(BonesMatematicaCog(bot))

        if not TOKEN:
            print("❌ ERRO: token não encontrado! Crie um .env com BONES_TOKEN=seu_token")
            return
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(_main())
