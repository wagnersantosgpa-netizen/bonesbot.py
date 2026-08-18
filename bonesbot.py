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
CHANCE_GATILHO_SEM_CHAMAR = 0.30   # chance de responder gatilho mesmo sem ser chamado

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
    ],
    "abraça": [
        "*envolve {alvo} num abraço de ossinhos* awwn!! 🦴🥹",
        "*abraça {alvo} apertado, os ossos rangendo de carinho* 💀💕",
        "*puxa {alvo} pra um abraço caloroso (e ossudo)* 🦴🤗",
    ],
    "beija": [
        "*dá um beijo de caveira em {alvo}* mwah!! cuidado com os dentinhos!! 💀😘",
        "*beija {alvo} de leve* 💀💋",
    ],
    "chuta": [
        "*dá um chutinho de osso em {alvo}* toma!! 🦴💥",
        "*chuta {alvo} com a canela de osso* PLOFT!! 💀🦴",
    ],
    "ataca": [
        "*avança sobre {alvo} chacoalhando os ossos* ATAQUEEE!! 💀⚔️",
        "*pula em cima de {alvo}* rá, se ferrou!! 🦴😈",
        "*investe contra {alvo} com tudo* CRACK CRACK!! 💀🦴",
    ],
    "cutuca": [
        "*cutuca {alvo} com o dedinho de osso* toc toc!! 🦴👀",
        "*fica cutucando {alvo} sem parar* toc toc toc!! 💀😆",
    ],
    "belisca": [
        "*belisca {alvo} de leve* ai, mentira, eu nem tenho carne pra beliscar!! kkkk 💀🦴",
    ],
    "empurra": [
        "*empurra {alvo} de leve* opa, sai da frente!! 🦴😆",
        "*dá um empurrãozinho em {alvo}* eita, com força não!! 💀",
    ],
    "ignora": [
        "*vira a caveira pro outro lado, ignorando {alvo}* 💀🙄",
        "*finge que não viu {alvo}* ... 👀💀",
    ],
    "acorda": [
        "*abre um olho da órbita vazia* hm?? já?? tá bom, acordei!! 😴💀",
        "*se espreguiça todo desconjuntado* ain, {alvo}, deixa eu dormir mais um pouco!! 💀😴",
    ],
    "chama": [
        "*aparece flutuando na hora* presente!! quem chamou?? 💀🦴",
    ],
    "bate": [
        "*leva a batida e os ossos chacoalham todos* AI!! (bom, sou só osso, não dói tanto) 💀😂",
    ],
    "assusta": [
        "*se assusta e os ossinhos voam pro alto* AAAAH!! 😱💀🦴",
        "*pula de susto, quase se desmonta* eita, {alvo}, quase me tirou um osso do lugar!! 💀😱",
    ],
    "rouba": [
        "*esconde os ossinhos rapidinho* ei, isso é meu, {alvo}!! 🦴😤",
    ],
    "brinca": [
        "*sacode animado, pronto pra brincar* eba, bora brincar!! 🦴✨",
    ],
    "foge": [
        "*sai flutuando rapidinho, os ossos voando pra trás* AAAH TCHAU!! 👻💀",
        "*foge de {alvo} chacoalhando todo* CRACK CRACK CORRE!! 🦴💨",
    ],
    "protege": [
        "*se põe na frente de {alvo}, escudo de osso ativado* pode vir, eu seguro!! 🦴🛡️",
    ],
    "cura": [
        "*balança os ossinhos numa dancinha mágica em cima de {alvo}* fica bom logo!! 🦴✨💫",
    ],
}

# Reações genéricas pra qualquer verbo que não esteja no dicionário acima —
# assim o Bones sempre reage a uma ação, mesmo que não reconheça o verbo.
_REACOES_RP_GENERICA = [
    "*entra na brincadeira mesmo sem entender direito a ação* 💀✨",
    "*balança os ossinhos, participando da cena* 🦴😄",
    "*reage do jeito que dá, sendo só um monte de osso* 💀🦴",
    "*se mexe desengonçado tentando acompanhar* 🦴😅",
]

# Reconhece mensagens no formato "Bones <verbo> <resto>" (RP de ação)
_PADRAO_ACAO_RP = re.compile(r"^bones\s+(\S+)\s*(.*)$", re.IGNORECASE)

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
]

# Também funciona como gatilho de diálogo comum — assim "Bones conte uma
# piada", "fala uma piada", "manda uma piada" etc. tudo cai aqui, não só
# o comando b!piada.
_RESPOSTAS_SEED["piada"] = list(_PIADAS_OSSOS)

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
        # Checa gatilhos mais específicos (mais longos) primeiro,
        # assim "tudo bem" não perde pra "oi" numa frase tipo "oi, tudo bem?"
        for chave in sorted(self.db["respostas"], key=len, reverse=True):
            if chave in texto_lower:
                return chave
        return None

    def _responder(self, chave: str) -> str:
        resps = self.db["respostas"].get(chave, [])
        return random.choice(resps) if resps else ""

    def _em_cooldown(self, channel_id: int, now: datetime) -> bool:
        ultimo = self._ultimo_resp.get(channel_id)
        return bool(ultimo and (now - ultimo).total_seconds() < COOLDOWN_RESPOSTA)

    def _detectar_reacao_rp(self, texto: str) -> str | None:
        """Detecta mensagens tipo 'Bones morde o vilão' e monta a reação."""
        m = _PADRAO_ACAO_RP.match(texto.strip())
        if not m:
            return None
        verbo = m.group(1).lower().strip(".,!?*")
        alvo = m.group(2).strip(" .,!?*") or "você"
        pool = _REACOES_RP.get(verbo, _REACOES_RP_GENERICA)
        return random.choice(pool).format(alvo=alvo)

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

        bones_mencionado = (
            self.bot.user in message.mentions
            or "bones" in message.content.lower()
        )

        chave = self._checar_gatilho(message.content)

        # ── 1) Gatilho conhecido: responde sempre que chamado,
        #        e às vezes mesmo sem ser chamado ──────────────
        if chave and (bones_mencionado or random.random() < CHANCE_GATILHO_SEM_CHAMAR):
            resp = self._responder(chave)
            if resp:
                self._ultimo_resp[message.channel.id] = now
                self._ultima_interacao[message.channel.id] = now
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(0.8, 1.8))
                await message.reply(resp, mention_author=False)
                return

        # ── 2) Foi chamado mas sem gatilho específico ───────
        if bones_mencionado and not chave:
            self._ultimo_resp[message.channel.id] = now
            self._ultima_interacao[message.channel.id] = now
            async with message.channel.typing():
                await asyncio.sleep(random.uniform(0.5, 1.2))

            reacao_rp = self._detectar_reacao_rp(message.content)
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
