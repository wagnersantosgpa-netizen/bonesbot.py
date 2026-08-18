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
CHANCE_ESPONTANEA = 0.015          # chance de aparecer do nada (por mensagem)
COOLDOWN_ESPONTANEA = 60           # só aparece do nada se fizer +60s calado no canal

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
    ],
    "bom dia": [
        "bom dia, ossinho(a)!! ☀️💀",
        "*espreguiça as costelinhas* bom dia!! 🦴✨",
        "bom diaaa!! energia de caveirinha ativada!! 💀☀️",
        "bom dia pra galera da OLS!! 💀🦴",
    ],
    "boa noite": [
        "boa noite, ossinho(a)!! durma bem!! 💀🌙",
        "*se enrola nos próprios ossos* boa noite!! 🦴🌙",
        "boa noiteee!! sonhos de caveirinha fofa pra você!! 💀✨",
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

    # ── Helpers internos ──────────────────────────────

    def _checar_gatilho(self, texto: str) -> str | None:
        texto_lower = texto.lower().strip()
        if texto_lower in self.db["respostas"]:
            return texto_lower
        for chave in self.db["respostas"]:
            if chave in texto_lower:
                return chave
        return None

    def _responder(self, chave: str) -> str:
        resps = self.db["respostas"].get(chave, [])
        return random.choice(resps) if resps else ""

    def _em_cooldown(self, channel_id: int, now: datetime) -> bool:
        ultimo = self._ultimo_resp.get(channel_id)
        return bool(ultimo and (now - ultimo).total_seconds() < COOLDOWN_RESPOSTA)

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
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(0.8, 1.8))
                await message.reply(resp, mention_author=False)
                return

        # ── 2) Foi chamado mas sem gatilho específico ───────
        if bones_mencionado and not chave:
            self._ultimo_resp[message.channel.id] = now
            async with message.channel.typing():
                await asyncio.sleep(random.uniform(0.5, 1.2))
            await message.reply(random.choice(_RESPOSTAS_MENCAO), mention_author=False)
            return

        # ── 3) Ninguém chamou, sem gatilho: chance de o Bones
        #        "aparecer do nada" de forma espontânea ───────
        if not bones_mencionado and not chave and random.random() < CHANCE_ESPONTANEA:
            ultimo = self._ultimo_resp.get(message.channel.id)
            if not ultimo or (now - ultimo).total_seconds() > COOLDOWN_ESPONTANEA:
                self._ultimo_resp[message.channel.id] = now
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(0.3, 0.8))
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
