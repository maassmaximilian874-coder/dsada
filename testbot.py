import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
 
# ─────────────────────────────────────────────
#  Konfiguration
# ─────────────────────────────────────────────
TOKEN = "MTE4MzgzODA1MDI0MjAwNzA3MQ.Gm0aX1.86yIOl8NOJTg-4wRufSIgULbc6QIuFNB2hRG3"   # <── hier deinen Token einfügen
 
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
 
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
 
 
# ─────────────────────────────────────────────
#  Events
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅  Bot eingeloggt als {bot.user} (ID: {bot.user.id})")
    print("⏳  Synchronisiere Slash Commands ...")
    # Global sync (nötig für User-Install / DM-Commands)
    try:
        await tree.sync()
        print("✅  Globale Commands synchronisiert")
    except Exception as e:
        print(f"❌  Fehler beim globalen Sync: {e}")
    # Guild-spezifischer Sync für schnellere Aktualisierung
    for guild in bot.guilds:
        try:
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
            print(f"✅  Commands synchronisiert für: {guild.name}")
        except Exception as e:
            print(f"❌  Fehler bei {guild.name}: {e}")
    print("─" * 40)
    print("🚀  Alle Commands bereit!")
 
 
# ─────────────────────────────────────────────
#  Snipe-Cache: Speichert letzte gelöschte Nachricht pro Channel
# ─────────────────────────────────────────────
snipe_cache: dict = {}  # channel_id -> {content, author, deleted_at, attachments}
 
@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot:
        return
    snipe_cache[message.channel.id] = {
        "content":     message.content or "*[kein Text]*",
        "author":      message.author,
        "deleted_at":  datetime.now(),
        "attachments": [a.url for a in message.attachments],
    }
 
 
# ─────────────────────────────────────────────
#  Hilfsfunktion: User per ID oder Mention holen
# ─────────────────────────────────────────────
async def resolve_user(interaction: discord.Interaction, user_input: str):
    user_input = user_input.strip("<@!>")
    try:
        user_id = int(user_input)
        user = await bot.fetch_user(user_id)
        return user
    except (ValueError, discord.NotFound):
        await interaction.followup.send("❌  User nicht gefunden. Nutze @Mention oder die User-ID.", ephemeral=True)
        return None
 
 
# ─────────────────────────────────────────────
#  /dm  <user>  <nachricht>
# ─────────────────────────────────────────────
@tree.command(name="dm", description="Schickt einem User eine DM")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user="@Mention oder User-ID", nachricht="Die Nachricht")
@app_commands.default_permissions(administrator=True)
async def slash_dm(interaction: discord.Interaction, user: str, nachricht: str):
    await interaction.response.defer(ephemeral=True)
    target = await resolve_user(interaction, user)
    if not target:
        return
    try:
        await target.send(nachricht)
        await interaction.followup.send(f"✉️  DM erfolgreich an **{target}** gesendet.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send(f"❌  Konnte keine DM an **{target}** senden (DMs deaktiviert oder Bot geblockt).", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌  Fehler: {e}", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /dmloop  <user>  <anzahl>  <nachricht>
# ─────────────────────────────────────────────
@tree.command(name="dmloop", description="Schickt einem User eine DM mehrfach (max. 1000)")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user="@Mention oder User-ID", anzahl="Wie oft (max. 1000)", nachricht="Die Nachricht")
@app_commands.default_permissions(administrator=True)
async def slash_dmloop(interaction: discord.Interaction, user: str, anzahl: int, nachricht: str):
    MAX = 1000
    if anzahl < 1 or anzahl > MAX:
        await interaction.response.send_message(f"⚠️  Anzahl muss zwischen 1 und {MAX} liegen.", ephemeral=True)
        return
 
    await interaction.response.defer(ephemeral=True)
    target = await resolve_user(interaction, user)
    if not target:
        return
 
    await interaction.followup.send(f"📨  Sende {anzahl}× DM an **{target}** …", ephemeral=True)
 
    sent = 0
    for i in range(anzahl):
        try:
            await target.send(nachricht)
            sent += 1
        except discord.Forbidden:
            await interaction.followup.send(f"❌  DM fehlgeschlagen (geblockt/DMs aus) nach {sent} Nachrichten.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌  Fehler bei Nachricht {i+1}: {e}", ephemeral=True)
            return
        if i < anzahl - 1:
            await asyncio.sleep(0.5)
 
    await interaction.followup.send(f"✅  {sent}/{anzahl} DMs erfolgreich gesendet.", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /schedule  <user>  <uhrzeit>  <nachricht>
# ─────────────────────────────────────────────
@tree.command(name="schedule", description="Plant eine DM zu einer bestimmten Uhrzeit (HH:MM)")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user="@Mention oder User-ID", uhrzeit="Format: HH:MM z.B. 18:30", nachricht="Die Nachricht")
@app_commands.default_permissions(administrator=True)
async def slash_schedule(interaction: discord.Interaction, user: str, uhrzeit: str, nachricht: str):
    try:
        hour, minute = map(int, uhrzeit.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await interaction.response.send_message("⚠️  Ungültige Uhrzeit. Format: `HH:MM` z.B. `18:30`", ephemeral=True)
        return
 
    await interaction.response.defer(ephemeral=True)
    target = await resolve_user(interaction, user)
    if not target:
        return
 
    now = datetime.now()
    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target_time <= now:
        target_time += timedelta(days=1)
 
    wait_seconds = (target_time - now).total_seconds()
    minutes_left = int(wait_seconds // 60)
 
    await interaction.followup.send(
        f"⏰  DM an **{target}** geplant für **{uhrzeit} Uhr** (in ~{minutes_left} Minuten).",
        ephemeral=True
    )
 
    await asyncio.sleep(wait_seconds)
 
    try:
        await target.send(nachricht)
        await interaction.followup.send(f"✅  Geplante DM erfolgreich an **{target}** gesendet.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send(f"❌  Konnte DM nicht senden (geblockt/DMs aus).", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌  Fehler: {e}", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /pingevery  <nachricht>
# ─────────────────────────────────────────────
@tree.command(name="pingevery", description="Pingt @everyone mit einer Nachricht")
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(nachricht="Nachricht nach dem Ping (optional)")
@app_commands.default_permissions(administrator=True)
async def slash_pingevery(interaction: discord.Interaction, nachricht: str = ""):
    await interaction.response.defer(ephemeral=True)
    text = f"@everyone {nachricht}" if nachricht else "@everyone"
    await interaction.channel.send(text, allowed_mentions=discord.AllowedMentions(everyone=True))
    await interaction.followup.send("✅  @everyone gepingt.", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /pinghere  <nachricht>
# ─────────────────────────────────────────────
@tree.command(name="pinghere", description="Pingt @here mit einer Nachricht")
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(nachricht="Nachricht nach dem Ping (optional)")
@app_commands.default_permissions(administrator=True)
async def slash_pinghere(interaction: discord.Interaction, nachricht: str = ""):
    await interaction.response.defer(ephemeral=True)
    text = f"@here {nachricht}" if nachricht else "@here"
    await interaction.channel.send(text, allowed_mentions=discord.AllowedMentions(everyone=True))
    await interaction.followup.send("✅  @here gepingt.", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /say  <nachricht>  <anzahl>
#  Schreibt eine Nachricht X-mal in den Channel.
# ─────────────────────────────────────────────
@tree.command(name="say", description="Schreibt eine Nachricht mehrmals in den Channel (max. 1000)")
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(nachricht="Die Nachricht", anzahl="Wie oft (max. 1000)")
@app_commands.default_permissions(administrator=True)
async def slash_say(interaction: discord.Interaction, nachricht: str, anzahl: int = 1):
    MAX = 1000
    if anzahl < 1 or anzahl > MAX:
        await interaction.response.send_message(f"⚠️  Anzahl muss zwischen 1 und {MAX} liegen.", ephemeral=True)
        return
 
    await interaction.response.defer(ephemeral=True)
 
    for i in range(anzahl):
        await interaction.channel.send(nachricht)
        if i < anzahl - 1:
            await asyncio.sleep(0.5)
 
    await interaction.followup.send(f"✅  Nachricht {anzahl}× gesendet.", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /pinguser  <user>  <anzahl>  <nachricht>
# ─────────────────────────────────────────────
@tree.command(name="pinguser", description="Pingt einen User mehrmals im Channel (max. 1000)")
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(user="@Mention oder User-ID", anzahl="Wie oft (max. 1000)", nachricht="Nachricht nach dem Ping (optional)")
@app_commands.default_permissions(administrator=True)
async def slash_pinguser(interaction: discord.Interaction, user: str, anzahl: int = 1, nachricht: str = ""):
    MAX = 1000
    if anzahl < 1 or anzahl > MAX:
        await interaction.response.send_message(f"⚠️  Anzahl muss zwischen 1 und {MAX} liegen.", ephemeral=True)
        return
 
    await interaction.response.defer(ephemeral=True)
    target = await resolve_user(interaction, user)
    if not target:
        return
 
    await interaction.followup.send(f"📣  Pinge **{target}** {anzahl}× …", ephemeral=True)
 
    for i in range(anzahl):
        text = f"{target.mention} {nachricht}" if nachricht else target.mention
        await interaction.channel.send(text, allowed_mentions=discord.AllowedMentions(users=True))
        if i < anzahl - 1:
            await asyncio.sleep(0.5)
 
    await interaction.followup.send(f"✅  **{target}** wurde {anzahl}× gepingt.", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /ghostping  <user>  <anzahl>
# ─────────────────────────────────────────────
@tree.command(name="ghostping", description="Ghostpingt einen User (Ping sofort gelöscht, max. 1000)")
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(user="@Mention oder User-ID", anzahl="Wie oft (max. 1000)")
@app_commands.default_permissions(administrator=True)
async def slash_ghostping(interaction: discord.Interaction, user: str, anzahl: int = 1):
    MAX = 1000
    if anzahl < 1 or anzahl > MAX:
        await interaction.response.send_message(f"⚠️  Anzahl muss zwischen 1 und {MAX} liegen.", ephemeral=True)
        return
 
    await interaction.response.defer(ephemeral=True)
    target = await resolve_user(interaction, user)
    if not target:
        return
 
    await interaction.followup.send(f"👻  Ghostpinge **{target}** {anzahl}× …", ephemeral=True)
 
    for i in range(anzahl):
        msg = await interaction.channel.send(target.mention, allowed_mentions=discord.AllowedMentions(users=True))
        await msg.delete()
        await asyncio.sleep(0.5)
 
    await interaction.followup.send(f"✅  **{target}** wurde {anzahl}× ghostgepingt.", ephemeral=True)
 
# ─────────────────────────────────────────────
#  /impersonate  <name>  <avatar_url>  <nachricht>
#  Sendet eine Nachricht als Webhook mit eigenem Namen & Avatar.
#  Beispiel: /impersonate name:Elon avatar:https://... nachricht:Hello World
# ─────────────────────────────────────────────
@tree.command(name="impersonate", description="Sendet eine Nachricht mit eigenem Namen & Avatar")
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(
    name="Name der angezeigt wird",
    nachricht="Die Nachricht",
    avatar_url="Avatar-URL (optional, muss mit https:// beginnen)"
)
@app_commands.default_permissions(administrator=True)
async def slash_impersonate(interaction: discord.Interaction, name: str, nachricht: str, avatar_url: str = None):
    await interaction.response.defer(ephemeral=True)
 
    # Webhook erstellen oder vorhandenen nutzen
    webhooks = await interaction.channel.webhooks()
    webhook = next((w for w in webhooks if w.name == "BotImpersonate"), None)
    if not webhook:
        webhook = await interaction.channel.create_webhook(name="BotImpersonate")
 
    try:
        await webhook.send(
            content=nachricht,
            username=name,
            avatar_url=avatar_url if avatar_url else discord.utils.MISSING
        )
        await interaction.followup.send(f"✅  Nachricht als **{name}** gesendet.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌  Fehler: {e}", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /fakeban  <user>
#  Sendet eine Fake-Ban-Nachricht an einen User per DM.
#  Beispiel: /fakeban user:123456789
# ─────────────────────────────────────────────
@tree.command(name="fakeban", description="Schickt einem User eine Fake-Ban-DM")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user="@Mention oder User-ID", grund="Grund für den Ban (optional)")
@app_commands.default_permissions(administrator=True)
async def slash_fakeban(interaction: discord.Interaction, user: str, grund: str = "Verstoß gegen die Serverregeln"):
    await interaction.response.defer(ephemeral=True)
    target = await resolve_user(interaction, user)
    if not target:
        return
    try:
        embed = discord.Embed(
            title="⛔  Du wurdest gebannt!",
            description=f"Du wurdest von **{interaction.guild.name}** permanent gebannt.",
            color=discord.Color.red()
        )
        embed.add_field(name="Grund", value=grund, inline=False)
        embed.add_field(name="Server", value=interaction.guild.name, inline=True)
        embed.set_footer(text="Discord Moderationssystem")
        await target.send(embed=embed)
        await interaction.followup.send(f"✅  Fake-Ban an **{target}** gesendet.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send(f"❌  Konnte keine DM an **{target}** senden.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌  Fehler: {e}", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /countdown  <sekunden>
#  Startet einen Countdown im Channel.
#  Beispiel: /countdown sekunden:10
# ─────────────────────────────────────────────
@tree.command(name="countdown", description="Startet einen Countdown im Channel")
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(sekunden="Countdown von (max. 60)", nachricht="Nachricht nach dem Countdown (optional)")
@app_commands.default_permissions(administrator=True)
async def slash_countdown(interaction: discord.Interaction, sekunden: int, nachricht: str = "🚀  Los geht's!"):
    if sekunden < 1 or sekunden > 60:
        await interaction.response.send_message("⚠️  Sekunden müssen zwischen 1 und 60 liegen.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    msg = await interaction.channel.send(f"⏳  **{sekunden}**")
    for i in range(sekunden - 1, 0, -1):
        await asyncio.sleep(1)
        await msg.edit(content=f"⏳  **{i}**")
    await asyncio.sleep(1)
    await msg.edit(content=f"**{nachricht}**")
    await interaction.followup.send("✅  Countdown fertig!", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /roast  <user>
#  KI generiert einen Roast über einen User.
#  Beispiel: /roast user:123456789
# ─────────────────────────────────────────────
@tree.command(name="roast", description="KI generiert einen Roast über einen User")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user="@Mention oder User-ID")
@app_commands.default_permissions(administrator=True)
async def slash_roast(interaction: discord.Interaction, user: str):
    await interaction.response.defer()
    target = await resolve_user(interaction, user)
    if not target:
        return
 
    prompt = f"Schreib einen lustigen, kreativen Roast auf Deutsch über einen Discord User namens '{target.display_name}'. Maximal 2 Sätze, witzig aber nicht zu gemein."
    roast_text = await call_claude(prompt, max_tokens=200)
    if not roast_text:
        roast_text = f"{target.display_name} ist so langweilig, selbst seine Fehler gähnen."
 
    embed = discord.Embed(
        title=f"🔥  Roast: {target.display_name}",
        description=roast_text,
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.followup.send(embed=embed)
 
 
 
# ─────────────────────────────────────────────
#  Hilfsfunktion: Claude API aufrufen
# ─────────────────────────────────────────────
async def call_claude(prompt: str, max_tokens: int = 300) -> str:
    import urllib.request
    import json
 
    data = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")
 
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    )
 
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return result["content"][0]["text"]
    except Exception:
        return None
 
 
# ─────────────────────────────────────────────
#  /compliment  <user>
#  KI generiert ein Kompliment über einen User.
# ─────────────────────────────────────────────
@tree.command(name="compliment", description="KI generiert ein Kompliment für einen User")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user="@Mention oder User-ID")
async def slash_compliment(interaction: discord.Interaction, user: str):
    await interaction.response.defer()
    target = await resolve_user(interaction, user)
    if not target:
        return
 
    prompt = f"Schreib ein aufrichtiges, herzliches Kompliment auf Deutsch für einen Discord User namens '{target.display_name}'. Maximal 2 Sätze, kreativ und nett."
    text = await call_claude(prompt)
    if not text:
        text = f"{target.display_name} ist einfach eine Bereicherung für jeden Server – man merkt sofort, dass hier ein besonderer Mensch unterwegs ist!"
 
    embed = discord.Embed(
        description=text,
        color=discord.Color.pink()
    )
    embed.set_author(
        name=f"💖  Kompliment für {target.display_name}",
        icon_url=target.display_avatar.url
    )
    embed.set_footer(text=f"Von {interaction.user.display_name}")
    await interaction.followup.send(embed=embed)
 
 
# ─────────────────────────────────────────────
#  /story  <thema>
#  KI schreibt eine kurze Geschichte.
# ─────────────────────────────────────────────
@tree.command(name="story", description="KI schreibt eine kurze Geschichte zu einem Thema")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(thema="Thema oder Stichwort für die Geschichte")
async def slash_story(interaction: discord.Interaction, thema: str):
    await interaction.response.defer()
 
    prompt = f"Schreib eine kurze, spannende oder lustige Geschichte auf Deutsch zum Thema '{thema}'. Maximal 5 Sätze, kreativ und unterhaltsam."
    text = await call_claude(prompt, max_tokens=400)
    if not text:
        text = "Es war einmal... leider ist dem Geschichtenerzähler gerade die Tinte ausgegangen. 📖"
 
    embed = discord.Embed(
        title=f"📖  Geschichte: {thema}",
        description=text,
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Angefragt von {interaction.user.display_name}")
    await interaction.followup.send(embed=embed)
 
 
# ─────────────────────────────────────────────
#  /rizz  <user>
#  KI generiert eine Anmachzeile für einen User.
# ─────────────────────────────────────────────
@tree.command(name="rizz", description="KI generiert eine Anmachzeile für einen User")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user="@Mention oder User-ID")
async def slash_rizz(interaction: discord.Interaction, user: str):
    await interaction.response.defer()
    target = await resolve_user(interaction, user)
    if not target:
        return
 
    prompt = f"Schreib eine witzige, charmante Anmachzeile auf Deutsch für jemanden namens '{target.display_name}'. Maximal 2 Sätze, kreativ, witzig aber nicht unanständig."
    text = await call_claude(prompt)
    if not text:
        text = f"Hey {target.display_name}, bist du ein WLAN-Passwort? Weil ich dich unbedingt haben möchte. 😏"
 
    embed = discord.Embed(
        description=text,
        color=discord.Color.gold()
    )
    embed.set_author(
        name=f"😏  Rizz für {target.display_name}",
        icon_url=target.display_avatar.url
    )
    embed.set_footer(text=f"Von {interaction.user.display_name}")
    await interaction.followup.send(embed=embed)
 
 
# ─────────────────────────────────────────────
#  /purge  <anzahl>
#  Löscht X Nachrichten im Channel auf einmal.
# ─────────────────────────────────────────────
@tree.command(name="purge", description="Löscht X Nachrichten im Channel (max. 1000)")
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(anzahl="Anzahl der zu löschenden Nachrichten (max. 1000)")
@app_commands.default_permissions(manage_messages=True)
async def slash_purge(interaction: discord.Interaction, anzahl: int):
    if anzahl < 1 or anzahl > 1000:
        await interaction.response.send_message("⚠️  Anzahl muss zwischen 1 und 1000 liegen.", ephemeral=True)
        return
 
    await interaction.response.defer(ephemeral=True)
 
    try:
        total_deleted = 0
        remaining = anzahl
        while remaining > 0:
            batch = min(remaining, 100)
            deleted = await interaction.channel.purge(limit=batch)
            total_deleted += len(deleted)
            remaining -= batch
            if len(deleted) < batch:
                break
            await asyncio.sleep(0.5)
        await interaction.followup.send(f"🗑️  **{total_deleted}** Nachrichten gelöscht.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌  Ich habe keine Berechtigung, Nachrichten zu löschen.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌  Fehler: {e}", ephemeral=True)
 
 
# ─────────────────────────────────────────────
#  /snipe
#  Zeigt die zuletzt gelöschte Nachricht im Channel.
#  Beispiel: /snipe
# ─────────────────────────────────────────────
@tree.command(name="snipe", description="Zeigt die zuletzt gelöschte Nachricht in diesem Channel")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def slash_snipe(interaction: discord.Interaction):
    data = snipe_cache.get(interaction.channel.id)
 
    if not data:
        await interaction.response.send_message(
            "🔍  Keine gelöschten Nachrichten im Cache (seit Bot-Start).",
            ephemeral=True
        )
        return
 
    delta = datetime.now() - data["deleted_at"]
    if delta.total_seconds() < 60:
        zeit_str = f"vor {int(delta.total_seconds())} Sekunden"
    elif delta.total_seconds() < 3600:
        zeit_str = f"vor {int(delta.total_seconds() // 60)} Minuten"
    else:
        zeit_str = f"vor {int(delta.total_seconds() // 3600)} Stunden"
 
    embed = discord.Embed(
        description=data["content"],
        color=discord.Color.red(),
        timestamp=data["deleted_at"]
    )
    embed.set_author(
        name=str(data["author"]),
        icon_url=data["author"].display_avatar.url
    )
    embed.set_footer(text=f"Gelöscht {zeit_str}")
 
    if data["attachments"]:
        embed.add_field(
            name="📎 Anhänge",
            value="\n".join(data["attachments"]),
            inline=False
        )
        # Erstes Bild direkt im Embed anzeigen
        embed.set_image(url=data["attachments"][0])
 
    await interaction.response.send_message(embed=embed)
 
 
# ─────────────────────────────────────────────
#  Start
# ─────────────────────────────────────────────
bot.run(TOKEN)